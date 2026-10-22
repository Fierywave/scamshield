import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import joblib
import scipy.sparse as sp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from app.rules import run_rules, URL_RE
from app.trusted import is_trusted
from app.url_features import url_features

app = FastAPI(title="ScamShield API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
engine = create_engine(os.environ["DATABASE_URL"])

MODELS = Path(__file__).parent / "models"
vec, clf = joblib.load(MODELS / "combined.joblib")
url_vec, url_scaler, url_clf, url_cols = joblib.load(MODELS / "url_model_v2.joblib")

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS cases (
        id SERIAL PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'under_review',
        created_at TIMESTAMPTZ DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS reports (
        id SERIAL PRIMARY KEY,
        text TEXT NOT NULL,
        verdict TEXT,
        score DOUBLE PRECISION,
        reasons TEXT,
        case_id INT REFERENCES cases(id),
        created_at TIMESTAMPTZ DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS report_entities (
        report_id INT REFERENCES reports(id) ON DELETE CASCADE,
        kind TEXT NOT NULL,
        value TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_entity ON report_entities (kind, value)",
]
with engine.begin() as _conn:
    for _stmt in SCHEMA:
        _conn.execute(text(_stmt))


def clean_url(u):
    u = re.sub(r"^https?://", "", str(u).lower())
    return re.sub(r"^www\.", "", u)


def url_probability(url):
    feats = url_features(url)
    nums = [[feats[c] for c in url_cols]]
    X = sp.hstack([url_vec.transform([clean_url(url)]), url_scaler.transform(nums)]).tocsr()
    return float(url_clf.predict_proba(X)[0][1])


def analyze_text(t):
    p = float(clf.predict_proba(vec.transform([t]))[0][1])
    reasons = run_rules(t)
    urls = URL_RE.findall(t)
    url_results = [
        {"url": u, "probability": 0.0 if is_trusted(u) else round(url_probability(u), 3)}
        for u in urls
    ]
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


def normalize_url(u):
    u = u.strip().rstrip(".,;)")
    p = urlparse(u if "://" in u else "http://" + u)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host, host + p.path.rstrip("/")


def fingerprint(t):
    t = URL_RE.sub("<url>", t.lower())
    t = re.sub(r"\d+", "<n>", t)
    t = re.sub(r"\s+", " ", t).strip()
    return hashlib.sha1(t.encode()).hexdigest()[:12]


def extract_entities(t):
    ents = {("fingerprint", fingerprint(t))}
    for u in URL_RE.findall(t):
        host, full = normalize_url(u)
        if host and not is_trusted(u):
            ents.add(("domain", host))
            ents.add(("url", full))
    return ents


PHONE_RE = re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)")
LONGNUM_RE = re.compile(r"(?<!\d)\d{9,18}(?!\d)")


def mask_pii(t):
    t = PHONE_RE.sub("[phone]", t)
    return LONGNUM_RE.sub("[number]", t)

class AnalyzeRequest(BaseModel):
    text: str


class StatusUpdate(BaseModel):
    status: str


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    return analyze_text(req.text)


@app.post("/reports")
def create_report(req: AnalyzeRequest):
    result = analyze_text(req.text)
    ents = extract_entities(req.text)
    flagged = result["verdict"] in ("scam", "suspicious")

    with engine.begin() as conn:
        rid = conn.execute(
            text("INSERT INTO reports (text, verdict, score, reasons) "
                 "VALUES (:t, :v, :s, :r) RETURNING id"),
            {"t": mask_pii(req.text), "v": result["verdict"], "s": result["score"],
             "r": json.dumps(result["reasons"])},
        ).scalar()
        for kind, value in ents:
            conn.execute(
                text("INSERT INTO report_entities (report_id, kind, value) VALUES (:r, :k, :v)"),
                {"r": rid, "k": kind, "v": value},
            )

        case_id = None
        if flagged:
            matched = set()
            for kind, value in ents:
                rows = conn.execute(
                    text("SELECT DISTINCT r.case_id FROM report_entities e "
                         "JOIN reports r ON r.id = e.report_id "
                         "WHERE e.kind = :k AND e.value = :v AND r.id <> :rid "
                         "AND r.case_id IS NOT NULL"),
                    {"k": kind, "v": value, "rid": rid},
                )
                matched.update(row[0] for row in rows)

            if matched:
                case_id = min(matched)
                others = sorted(c for c in matched if c != case_id)
                if others:
                    conn.execute(
                        text("UPDATE reports SET case_id = :c "
                             "WHERE case_id = ANY(CAST(:o AS int[]))"),
                        {"c": case_id, "o": others},
                    )
                    conn.execute(
                        text("DELETE FROM cases WHERE id = ANY(CAST(:o AS int[]))"),
                        {"o": others},
                    )
            else:
                case_id = conn.execute(text("INSERT INTO cases DEFAULT VALUES RETURNING id")).scalar()

            conn.execute(
                text("UPDATE reports SET case_id = :c WHERE id = :r"),
                {"c": case_id, "r": rid},
            )

        size = 0
        if case_id:
            size = conn.execute(
                text("SELECT count(*) FROM reports WHERE case_id = :c"), {"c": case_id}
            ).scalar()

    return {**result, "report_id": rid, "case_id": case_id, "case_size": size}


@app.get("/cases")
def list_cases():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT c.id, c.status, c.created_at, count(r.id) AS reports, "
            "max(r.score) AS max_score FROM cases c "
            "JOIN reports r ON r.case_id = c.id "
            "GROUP BY c.id ORDER BY count(r.id) DESC, c.id DESC LIMIT 100"
        )).mappings().all()
    return [dict(r) for r in rows]


@app.get("/cases/{case_id}")
def get_case(case_id: int):
    with engine.connect() as conn:
        case = conn.execute(
            text("SELECT id, status, created_at FROM cases WHERE id = :c"), {"c": case_id}
        ).mappings().first()
        if not case:
            raise HTTPException(404, "Case not found")
        reports = conn.execute(
            text("SELECT id, text, verdict, score, reasons, created_at FROM reports "
                 "WHERE case_id = :c ORDER BY id"), {"c": case_id}
        ).mappings().all()
        shared = conn.execute(
            text("SELECT e.kind, e.value, count(DISTINCT e.report_id) AS reports "
                 "FROM report_entities e JOIN reports r ON r.id = e.report_id "
                 "WHERE r.case_id = :c GROUP BY e.kind, e.value "
                 "HAVING count(DISTINCT e.report_id) > 1 ORDER BY reports DESC"),
            {"c": case_id},
        ).mappings().all()
    out = []
    for r in reports:
        d = dict(r)
        d["reasons"] = json.loads(d["reasons"] or "[]")
        out.append(d)
    return {**dict(case), "reports": out, "shared_evidence": [dict(s) for s in shared]}


@app.patch("/cases/{case_id}")
def update_case(case_id: int, body: StatusUpdate):
    if body.status not in ("under_review", "confirmed", "rejected"):
        raise HTTPException(400, "Status must be under_review, confirmed, or rejected")
    with engine.begin() as conn:
        n = conn.execute(
            text("UPDATE cases SET status = :s WHERE id = :c"),
            {"s": body.status, "c": case_id},
        ).rowcount
    if not n:
        raise HTTPException(404, "Case not found")
    return {"id": case_id, "status": body.status}

