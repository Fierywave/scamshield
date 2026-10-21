import re, math
from collections import Counter

KEYWORDS = ["login", "verify", "update", "secure", "account", "kyc", "bank", "confirm", "free", "bonus", "wallet"]
BAD_TLDS = (".xyz", ".top", ".click", ".link", ".live", ".online", ".site", ".tk", ".gq", ".ml", ".cf")

def entropy(s):
    if not s:
        return 0.0
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())

def url_features(url):
    # Strip scheme and www so the model cannot cheat on "http" vs "https" quirks in the dataset
    u = re.sub(r"^https?://", "", str(url).lower())
    u = re.sub(r"^www\.", "", u)
    host = u.split("/")[0].split(":")[0]
    path = u[len(host):]
    return {
        "url_len": len(u),
        "host_len": len(host),
        "path_len": len(path),
        "dots": host.count("."),
        "hyphens": host.count("-"),
        "digits": sum(ch.isdigit() for ch in u),
        "digit_ratio": sum(ch.isdigit() for ch in u) / max(len(u), 1),
        "special": sum(not ch.isalnum() and ch not in "./-" for ch in u),
        "has_at": int("@" in u),
        "is_ip": int(bool(re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host))),
        "bad_tld": int(host.endswith(BAD_TLDS)),
        "keywords": sum(k in u for k in KEYWORDS),
        "host_entropy": entropy(host),
        "path_depth": path.count("/"),
    }
