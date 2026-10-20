import os
from pathlib import Path
import joblib
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from app.rules import run_rules

app = FastAPI(title="ScamShield API")
engine = create_engine(os.environ["DATABASE_URL"])

MODEL_PATH = Path(__file__).parent / "models" / "combined.joblib"
vec, clf = joblib.load(MODEL_PATH)


class AnalyzeRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    p = float(clf.predict_proba(vec.transform([req.text]))[0][1])
    reasons = run_rules(req.text)
    strong = [r for r in reasons if "imitates" in r or "secret" in r]
    score = min(1.0, p + 0.08 * len(reasons))
    if strong:
        score = max(score, 0.7)
    if score >= 0.7:
        verdict = "scam"
    elif score >= 0.4:
        verdict = "suspicious"
    else:
        verdict = "likely safe"
    return {
        "verdict": verdict,
        "score": round(score, 3),
        "ml_probability": round(p, 3),
        "reasons": reasons,
    }
