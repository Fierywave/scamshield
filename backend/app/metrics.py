from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.auth import engine, require_analyst

router = APIRouter()


def ratio(a, b):
    return round(a / b, 4) if b else None


@router.get("/metrics")
def metrics(user=Depends(require_analyst)):
    with engine.connect() as c:
        t = c.execute(text(
            "SELECT count(*) AS total, "
            "coalesce(sum(flagged), 0) AS flagged, "
            "coalesce(sum(is_fraud), 0) AS fraud, "
            "coalesce(sum(CASE WHEN flagged = 1 AND is_fraud = 1 THEN 1 ELSE 0 END), 0) AS tp, "
            "coalesce(sum(CASE WHEN flagged = 1 AND is_fraud = 0 THEN 1 ELSE 0 END), 0) AS fp, "
            "coalesce(sum(CASE WHEN flagged = 0 AND is_fraud = 1 THEN 1 ELSE 0 END), 0) AS fn, "
            "percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50_ms, "
            "percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99_ms "
            "FROM txn_scores"
        )).mappings().first()
        patterns = c.execute(text(
            "SELECT pattern, count(*) AS fraud, "
            "sum(CASE WHEN flagged = 1 THEN 1 ELSE 0 END) AS caught "
            "FROM txn_scores WHERE is_fraud = 1 GROUP BY pattern ORDER BY pattern"
        )).mappings().all()
        verdicts = c.execute(text(
            "SELECT verdict, count(*) AS n FROM reports GROUP BY verdict"
        )).mappings().all()
        statuses = c.execute(text(
            "SELECT status, count(*) AS n FROM cases GROUP BY status"
        )).mappings().all()

    total, tp, fp, fn = int(t["total"]), int(t["tp"]), int(t["fp"]), int(t["fn"])
    negatives = total - int(t["fraud"])
    return {
        "transactions": {
            "total": total,
            "flagged": int(t["flagged"]),
            "fraud": int(t["fraud"]),
            "tp": tp, "fp": fp, "fn": fn,
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn),
            "false_positive_rate": ratio(fp, negatives),
            "p50_ms": t["p50_ms"],
            "p99_ms": t["p99_ms"],
        },
        "by_pattern": [
            {"pattern": p["pattern"], "fraud": int(p["fraud"]),
             "caught": int(p["caught"]), "recall": ratio(int(p["caught"]), int(p["fraud"]))}
            for p in patterns
        ],
        "reports": {v["verdict"]: int(v["n"]) for v in verdicts},
        "cases": {s["status"]: int(s["n"]) for s in statuses},
    }


@router.get("/transactions/flagged")
def flagged_transactions(user=Depends(require_analyst)):
    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT id, user_id, amount, pattern, is_fraud, ml_prob, rule_hit, reasons "
            "FROM txn_scores WHERE flagged = 1 ORDER BY id DESC LIMIT 50"
        )).mappings().all()
    return [dict(r) for r in rows]
