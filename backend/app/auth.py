import os
import time

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import create_engine, text

SECRET = os.environ.get("JWT_SECRET", "dev-only-change-me")
engine = create_engine(os.environ["DATABASE_URL"])
router = APIRouter()
bearer = HTTPBearer(auto_error=False)

with engine.begin() as _c:
    _c.execute(text("""CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'analyst',
        created_at TIMESTAMPTZ DEFAULT now())"""))
    _c.execute(text("""CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        user_email TEXT,
        action TEXT NOT NULL,
        case_id INT,
        detail TEXT,
        created_at TIMESTAMPTZ DEFAULT now())"""))


def log_action(email, action, case_id=None, detail=""):
    with engine.begin() as c:
        c.execute(
            text("INSERT INTO audit_log (user_email, action, case_id, detail) "
                 "VALUES (:e, :a, :c, :d)"),
            {"e": email, "a": action, "c": case_id, "d": detail},
        )


def require_analyst(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if creds is None:
        raise HTTPException(401, "Login required")
    try:
        data = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    if data.get("role") not in ("analyst", "admin"):
        raise HTTPException(403, "Analyst access only")
    return {"email": data["sub"], "role": data["role"]}


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(req: LoginRequest):
    email = req.email.strip().lower()
    with engine.connect() as c:
        row = c.execute(
            text("SELECT password_hash, role FROM users WHERE email = :e"), {"e": email}
        ).first()
    ok = bool(row) and bcrypt.checkpw(req.password.encode(), row[0].encode())
    if not ok:
        log_action(email, "login_failed")
        raise HTTPException(401, "Wrong email or password")
    token = jwt.encode(
        {"sub": email, "role": row[1], "exp": int(time.time()) + 8 * 3600},
        SECRET, algorithm="HS256",
    )
    log_action(email, "login")
    return {"token": token, "role": row[1]}


@router.get("/audit")
def audit(user=Depends(require_analyst)):
    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT id, user_email, action, case_id, detail, created_at "
            "FROM audit_log ORDER BY id DESC LIMIT 100"
        )).mappings().all()
    return [dict(r) for r in rows]
