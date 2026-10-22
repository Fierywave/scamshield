import getpass
import sys

import bcrypt
from sqlalchemy import text

from app.auth import engine

if len(sys.argv) < 2:
    sys.exit("Usage: python -m app.create_user <email> [role]")
email = sys.argv[1].strip().lower()
role = sys.argv[2] if len(sys.argv) > 2 else "analyst"
password = getpass.getpass("Password (min 8 characters): ")
if len(password) < 8:
    sys.exit("Password too short")

h = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
with engine.begin() as c:
    c.execute(
        text("INSERT INTO users (email, password_hash, role) VALUES (:e, :h, :r) "
             "ON CONFLICT (email) DO UPDATE SET password_hash = :h, role = :r"),
        {"e": email, "h": h, "r": role},
    )
print("Saved", email, "as", role)
