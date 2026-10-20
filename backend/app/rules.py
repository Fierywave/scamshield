import re
from urllib.parse import urlparse

URL_RE = re.compile(r"(?:https?://|www\.)[^\s]+", re.I)
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "rb.gy", "is.gd"}
BAD_TLDS = (".xyz", ".top", ".click", ".link", ".live", ".online", ".site", ".tk", ".gq", ".ml", ".cf")
BRANDS = {
    "sbi": {"sbi.co.in", "onlinesbi.sbi"},
    "icici": {"icicibank.com"},
    "hdfc": {"hdfcbank.com"},
    "axis": {"axisbank.com"},
    "paytm": {"paytm.com"},
    "phonepe": {"phonepe.com"},
    "amazon": {"amazon.in", "amazon.com"},
}

URGENCY = re.compile(r"\b(immediately|urgent|expires?|within 24 hours|last warning|act now|today itself|tonight|blocked|suspended|disconnected)\b", re.I)
KYC = re.compile(r"\b(kyc|pan card|aadhaar|aadhar)\b", re.I)
PRIZE = re.compile(r"\b(you won|won a prize|lottery|lucky draw|claim your reward|cashback offer)\b", re.I)
FEE = re.compile(r"\b(pay|deposit)\b.{0,40}\b(fee|charge|deposit)\b", re.I)
SECRET_ASK = re.compile(r"\b(share|send|tell|give|enter)\b.{0,25}\b(otp|cvv|pin|password)\b", re.I)
SAFE_OTP = re.compile(r"(do not|don't|never)\s+share", re.I)


def check_url(url):
    reasons = []
    host = (urlparse(url if "://" in url else "http://" + url).hostname or "").lower()
    if host in SHORTENERS:
        reasons.append("Uses a shortened link that hides the real destination.")
    if host.endswith(BAD_TLDS):
        reasons.append("Link uses a domain ending often seen in scam sites.")
    for brand, official in BRANDS.items():
        if brand in host and not any(host == d or host.endswith("." + d) for d in official):
            reasons.append(f"Link imitates '{brand}' but is not an official domain.")
    return reasons


def run_rules(text):
    reasons = []
    if URGENCY.search(text):
        reasons.append("Creates urgency or threatens suspension or disconnection.")
    if KYC.search(text):
        reasons.append("Mentions KYC or ID documents, a common phishing hook.")
    if PRIZE.search(text):
        reasons.append("Claims a prize or reward you did not ask for.")
    if FEE.search(text):
        reasons.append("Asks you to pay a fee to receive something.")
    if SECRET_ASK.search(text) and not SAFE_OTP.search(text):
        reasons.append("Asks you to share a secret such as an OTP, PIN, or password.")
    urls = URL_RE.findall(text)
    if urls:
        reasons.append("Contains a link. Do not open it without verifying the sender.")
        for u in urls:
            reasons.extend(check_url(u))
    return list(dict.fromkeys(reasons))
