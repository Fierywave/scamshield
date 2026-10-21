import os
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import redis
import xgboost as xgb
from sqlalchemy import create_engine, text

FEATURES = ["amount", "amount_ratio", "is_new_payee", "txn_count_10m",
            "new_payees_1h", "hour", "is_night", "secs_since_last"]
STREAM, GROUP, CONSUMER = "transactions", "scorers", "worker-1"

model = joblib.load(Path(__file__).parent / "models" / "txn_model.joblib")
booster = model.get_booster()
engine = create_engine(os.environ["DATABASE_URL"])
r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
STATE = {}

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS txn_scores (
    id SERIAL PRIMARY KEY,
    user_id INT, ts DOUBLE PRECISION, payee TEXT, amount DOUBLE PRECISION,
    is_fraud INT, pattern TEXT, ml_prob DOUBLE PRECISION, rule_hit INT,
    flagged INT, reasons TEXT, latency_ms DOUBLE PRECISION,
    scored_at TIMESTAMPTZ DEFAULT now()
)
"""
INSERT = text("""
INSERT INTO txn_scores (user_id, ts, payee, amount, is_fraud, pattern, ml_prob,
                        rule_hit, flagged, reasons, latency_ms)
VALUES (:user_id, :ts, :payee, :amount, :is_fraud, :pattern, :ml_prob,
        :rule_hit, :flagged, :reasons, :latency_ms)
""")


def setup():
    for _ in range(30):
        try:
            with engine.begin() as conn:
                conn.execute(text(CREATE_SQL))
            r.ping()
            break
        except Exception as e:
            print("Waiting for services:", e, flush=True)
            time.sleep(2)
    try:
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def make_features(f):
    s = STATE.setdefault(int(f["user"]), {"seen": set(), "amts": [], "times": [], "new": []})
    ts, payee, amount = float(f["ts"]), f["payee"], float(f["amount"])
    is_new = payee not in s["seen"]
    base = float(np.median(s["amts"])) if len(s["amts"]) >= 3 else 700.0
    hour = (ts / 3600) % 24
    feats = {
        "amount": amount,
        "amount_ratio": amount / base,
        "is_new_payee": int(is_new),
        "txn_count_10m": sum(1 for t in s["times"] if ts - t <= 600),
        "new_payees_1h": sum(1 for t in s["new"] if ts - t <= 3600),
        "hour": hour,
        "is_night": int(hour < 5 or hour >= 23),
        "secs_since_last": ts - s["times"][-1] if s["times"] else 1e6,
    }
    s["seen"].add(payee)
    s["amts"].append(amount)
    s["times"].append(ts)
    if is_new:
        s["new"].append(ts)
    return feats


def label(name, f):
    if name == "amount_ratio" and f["amount_ratio"] > 2:
        return f"Amount is {f['amount_ratio']:.1f}x this user's typical payment"
    if name == "is_new_payee" and f["is_new_payee"]:
        return "Payee has not been paid before"
    if name == "txn_count_10m" and f["txn_count_10m"] > 0:
        return f"{f['txn_count_10m']} earlier transactions in the last 10 minutes"
    if name == "new_payees_1h" and f["new_payees_1h"] > 0:
        return f"{f['new_payees_1h']} new payees in the last hour"
    if name == "is_night" and f["is_night"]:
        return "Made late at night"
    if name == "secs_since_last" and f["secs_since_last"] < 300:
        return "Very soon after the previous transaction"
    if name == "amount" and f["amount"] > 10000:
        return f"Large amount (Rs {f['amount']:.0f})"
    return None


def model_reasons(ft, contrib):
    out = []
    for j in np.argsort(-contrib[:-1])[:4]:
        if contrib[j] <= 0.3:
            break
        t = label(FEATURES[j], ft)
        if t:
            out.append(t)
    return out


def rule_reasons(ft):
    out = []
    if ft["is_new_payee"] == 1 and ft["amount_ratio"] > 5:
        out.append(f"Rule: new payee and amount is {ft['amount_ratio']:.1f}x the user's usual")
    if ft["txn_count_10m"] >= 4:
        out.append(f"Rule: {ft['txn_count_10m']} earlier transactions in the last 10 minutes")
    return out


def process(msgs):
    feats = [make_features(f) for _, f in msgs]
    df = pd.DataFrame(feats, columns=FEATURES)
    probs = model.predict_proba(df)[:, 1]
    ml_flag = probs >= 0.5
    idx = np.where(ml_flag)[0]
    contribs = {}
    if len(idx):
        c = booster.predict(xgb.DMatrix(df.iloc[idx]), pred_contribs=True)
        contribs = dict(zip(idx.tolist(), c))

    now = time.time()
    rows = []
    for i, (_, f) in enumerate(msgs):
        ft = feats[i]
        rule_hit = int((ft["is_new_payee"] == 1 and ft["amount_ratio"] > 5) or ft["txn_count_10m"] >= 4)
        reasons = []
        if i in contribs:
            reasons += model_reasons(ft, contribs[i])
        if rule_hit:
            reasons += rule_reasons(ft)
        flagged = int(bool(ml_flag[i]) or bool(rule_hit))
        if flagged and not reasons:
            reasons = ["Pattern is unusual for this user"]
        rows.append({
            "user_id": int(f["user"]), "ts": float(f["ts"]), "payee": f["payee"],
            "amount": float(f["amount"]), "is_fraud": int(f["is_fraud"]), "pattern": f["pattern"],
            "ml_prob": round(float(probs[i]), 4), "rule_hit": rule_hit, "flagged": flagged,
            "reasons": " | ".join(dict.fromkeys(reasons)),
            "latency_ms": (now - float(f["sent_at"])) * 1000,
        })
    return rows


if __name__ == "__main__":
    setup()
    print("Worker ready, waiting for transactions", flush=True)
    done = 0
    while True:
        resp = r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=100, block=1000)
        if not resp:
            continue
        msgs = resp[0][1]
        rows = process(msgs)
        with engine.begin() as conn:
            conn.execute(INSERT, rows)
        r.xack(STREAM, GROUP, *[m[0] for m in msgs])
        done += len(msgs)
        print(f"Scored {done}", flush=True)
