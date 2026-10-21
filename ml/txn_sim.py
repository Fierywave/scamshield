import numpy as np
import pandas as pd

FEATURES = ["amount", "amount_ratio", "is_new_payee", "txn_count_10m",
            "new_payees_1h", "hour", "is_night", "secs_since_last"]


def simulate(n_users=1000, days=30, n_fraud=450, seed=42):
    rng = np.random.default_rng(seed)
    users = []
    for u in range(n_users):
        users.append({
            "user": u,
            "mu": rng.normal(6.5, 0.6),
            "sigma": rng.uniform(0.5, 0.9),
            "hour": rng.uniform(9, 20),
            "rate": rng.uniform(0.7, 3.0),
            "payees": [f"P{u}_{i}" for i in range(int(rng.integers(5, 15)))],
        })

    rows = []
    for p in users:
        for _ in range(rng.poisson(p["rate"] * days)):
            day = int(rng.integers(0, days))
            hour = rng.normal(p["hour"], 3.0) % 24
            ts = day * 86400 + hour * 3600 + rng.uniform(0, 60)
            if rng.random() < 0.85:
                payee = p["payees"][int(rng.integers(len(p["payees"])))]
            else:
                payee = f"M{int(rng.integers(0, 50000))}"
            amount = float(np.exp(rng.normal(p["mu"], p["sigma"])))
            rows.append((p["user"], ts, payee, round(amount, 2), 0, "normal"))

    patterns = ["takeover", "test_then_drain", "scam_pay"]
    for i in range(n_fraud):
        p = users[int(rng.integers(n_users))]
        pat = patterns[i % 3]
        start = int(rng.integers(2, days)) * 86400
        typical = float(np.exp(p["mu"]))
        if pat == "takeover":
            t0 = start + rng.uniform(0, 5) * 3600
            for k in range(int(rng.integers(4, 9))):
                rows.append((p["user"], t0 + k * rng.uniform(30, 150), f"F{i}_{k}",
                             round(typical * rng.uniform(5, 20), 2), 1, pat))
        elif pat == "test_then_drain":
            t0 = start + rng.uniform(10, 22) * 3600
            rows.append((p["user"], t0, f"F{i}", round(rng.uniform(1, 10), 2), 1, pat))
            rows.append((p["user"], t0 + rng.uniform(120, 600), f"F{i}",
                         round(typical * rng.uniform(8, 25), 2), 1, pat))
        else:
            t0 = start + rng.uniform(10, 20) * 3600
            rows.append((p["user"], t0, f"F{i}", round(typical * rng.uniform(8, 30), 2), 1, pat))

    return pd.DataFrame(rows, columns=["user", "ts", "payee", "amount", "is_fraud", "pattern"])


def add_features(df):
    df = df.sort_values(["user", "ts"]).reset_index(drop=True)
    out = {k: [] for k in FEATURES}
    for _, g in df.groupby("user", sort=False):
        seen, amts, times, new_times = set(), [], [], []
        for ts, payee, amt in zip(g["ts"], g["payee"], g["amount"]):
            is_new = payee not in seen
            base = float(np.median(amts)) if len(amts) >= 3 else 700.0
            hour = (ts / 3600) % 24
            out["amount"].append(amt)
            out["amount_ratio"].append(amt / base)
            out["is_new_payee"].append(int(is_new))
            out["txn_count_10m"].append(sum(1 for t in times if ts - t <= 600))
            out["new_payees_1h"].append(sum(1 for t in new_times if ts - t <= 3600))
            out["hour"].append(hour)
            out["is_night"].append(int(hour < 5 or hour >= 23))
            out["secs_since_last"].append(ts - times[-1] if times else 1e6)
            seen.add(payee)
            amts.append(amt)
            times.append(ts)
            if is_new:
                new_times.append(ts)
    return df, pd.DataFrame(out)
