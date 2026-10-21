import os
from pathlib import Path
import joblib
import re
import scipy.sparse as sp
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from app.rules import run_rules, URL_RE
from app.url_features import url_features
from app.trusted import is_trusted
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ScamShield API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])
engine = create_engine(os.environ["DATABASE_URL"])

MODELS = Path(__file__).parent / "models"
vec, clf = joblib.load(MODELS / "combined.joblib")
url_vec, url_scaler, url_clf, url_cols = joblib.load(MODELS / "url_model_v2.joblib")


def clean_url(u):
    u = re.sub(r"^https?://", "", str(u).lower())
    return re.sub(r"^www\.", "", u)


def url_probability(url):
    feats = url_features(url)
    nums = [[feats[c] for c in url_cols]]
    X = sp.hstack([url_vec.transform([clean_url(url)]), url_scaler.transform(nums)]).tocsr()
    return float(url_clf.predict_proba(X)[0][1])


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

    urls = URL_RE.findall(req.text)
    url_results = [{"url": u, "probability": 0.0 if is_trusted(u) else round(url_probability(u), 3)} for u in urls]
    worst = max((r["probability"] for r in url_results), default=0.0)
    if worst >= 0.7:
        reasons.append("Our link classifier rates this link as likely malicious.")

    strong = [r for r in reasons if "imitates" in r or "secret" in r]
    score = min(1.0, p + 0.08 * len(reasons))
    if worst >= 0.7:
        score = min(1.0, score + 0.2)
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
        "urls": url_results,
        "reasons": reasons,
    }

