import os
from pathlib import Path
import joblib
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, text

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
    if p >= 0.7:
        verdict = "scam"
    elif p >= 0.4:
        verdict = "suspicious"
    else:
        verdict = "likely safe"
    return {"scam_probability": round(p, 3), "verdict": verdict}
