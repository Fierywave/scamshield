TRUSTED = {
    "amazon.in", "amazon.com", "sbi.co.in", "onlinesbi.sbi", "icicibank.com",
    "hdfcbank.com", "axisbank.com", "paytm.com", "phonepe.com", "google.com",
    "npci.org.in", "rbi.org.in", "cybercrime.gov.in", "irctc.co.in",
}

def is_trusted(url):
    from urllib.parse import urlparse
    host = (urlparse(url if "://" in url else "http://" + url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in TRUSTED)
