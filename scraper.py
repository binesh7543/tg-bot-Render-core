"""
scraper.py - Vehicle document check (Step 1: feasibility test)

Kaam: gadi ka number do -> Insurance / Fitness / PUC ki expiry date wapas do.

IMPORTANT (honest note):
- Niche PORTAL_* wale URLs aur field names UNVERIFIED hain. Mere paas
  portal ka live access nahi tha, isliye ye sirf skeleton hai.
- Pehla test `debug=True` se chalao. Wo raw response dikhayega, phir
  hum sahi URL / fields yahan fix karenge.
- Captcha OCR (ddddocr) 100% accurate nahi hota, isliye retry laga hai.
- Low volume rakho (1-2 request/sec se zyada nahi), portal ko pareshan mat karo.
"""

import re
import time
from datetime import datetime, date

import requests

# ---------------------------------------------------------------------
# CONFIG (inhe baad mein verify karke fix karna hai)
# ---------------------------------------------------------------------
PORTAL_BASE = "https://vahan.parivahan.gov.in"            # UNVERIFIED
PORTAL_HOME = PORTAL_BASE + "/nrservices/"                # UNVERIFIED
PORTAL_CAPTCHA = PORTAL_BASE + "/nrservices/captcha"      # UNVERIFIED
PORTAL_QUERY = PORTAL_BASE + "/nrservices/query"          # UNVERIFIED

TIMEOUT = 20
MAX_CAPTCHA_TRIES = 3
EXPIRING_SOON_DAYS = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

_ocr = None  # lazy load, kyunki ddddocr import bhaari hai


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def normalize_reg_no(reg_no: str) -> str:
    """'od 02 ab-1234' -> 'OD02AB1234'"""
    return re.sub(r"[^A-Z0-9]", "", (reg_no or "").upper())


def is_valid_reg_no(reg_no: str) -> bool:
    """Simple Indian format check: 2 letters + 1-2 digits + 0-3 letters + 4 digits."""
    return bool(re.fullmatch(r"[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{4}", reg_no))


def parse_date(text: str):
    """Kai date formats handle karta hai. Fail ho to None."""
    if not text:
        return None
    text = text.strip()
    for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def doc_status(expiry: date | None) -> dict:
    """Expiry date se status: valid / expiring / expired / unknown."""
    if expiry is None:
        return {"status": "unknown", "icon": "⚪", "expiry": None, "days_left": None}
    days_left = (expiry - date.today()).days
    if days_left < 0:
        status, icon = "expired", "🔴"
    elif days_left <= EXPIRING_SOON_DAYS:
        status, icon = "expiring", "🟡"
    else:
        status, icon = "valid", "🟢"
    return {
        "status": status,
        "icon": icon,
        "expiry": expiry.isoformat(),
        "days_left": days_left,
    }


# ---------------------------------------------------------------------
# Captcha
# ---------------------------------------------------------------------
def solve_captcha(image_bytes: bytes) -> str:
    global _ocr
    if _ocr is None:
        import ddddocr  # pip: ddddocr
        _ocr = ddddocr.DdddOcr(show_ad=False)
    return _ocr.classification(image_bytes).strip()


def fetch_captcha(session: requests.Session) -> bytes:
    """UNVERIFIED: portal ka asli captcha endpoint check karna hai."""
    r = session.get(PORTAL_CAPTCHA, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content


# ---------------------------------------------------------------------
# Query + parse
# ---------------------------------------------------------------------
def submit_query(session: requests.Session, reg_no: str, captcha_text: str) -> str:
    """UNVERIFIED: form field names (regn_no, captcha) portal se match karne hain."""
    payload = {
        "regn_no": reg_no,
        "captcha": captcha_text,
    }
    r = session.post(PORTAL_QUERY, data=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def _find_after_label(html: str, labels: list[str]) -> str | None:
    """Label ke baad aane wali date dhundo (HTML tags ignore karke)."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    for label in labels:
        m = re.search(
            re.escape(label) + r"\s*[:\-]?\s*(\d{1,2}[-/ ][A-Za-z0-9]{1,3}[-/ ]\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        if m:
            return m.group(1)
    return None


def parse_response(html: str) -> dict:
    return {
        "insurance": doc_status(parse_date(_find_after_label(
            html, ["Insurance Upto", "Insurance Valid Upto", "Insurance Expiry"]))),
        "fitness": doc_status(parse_date(_find_after_label(
            html, ["Fitness Upto", "Fitness Valid Upto", "Fitness Expiry"]))),
        "puc": doc_status(parse_date(_find_after_label(
            html, ["PUCC Upto", "PUC Upto", "Pollution Upto", "PUC Valid Upto"]))),
    }


def captcha_rejected(html: str) -> bool:
    return bool(re.search(r"invalid\s+captcha|captcha\s+(mismatch|incorrect)", html, re.I))


# ---------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------
def check_vehicle(reg_no: str, debug: bool = False) -> dict:
    reg_no = normalize_reg_no(reg_no)
    if not is_valid_reg_no(reg_no):
        return {"ok": False, "error": "invalid_vehicle_number", "vehicle": reg_no}

    session = requests.Session()
    session.headers.update(HEADERS)

    last_html = ""
    try:
        session.get(PORTAL_HOME, timeout=TIMEOUT)  # cookies / session set karne ke liye

        for attempt in range(1, MAX_CAPTCHA_TRIES + 1):
            captcha_text = solve_captcha(fetch_captcha(session))
            last_html = submit_query(session, reg_no, captcha_text)

            if captcha_rejected(last_html):
                time.sleep(1)  # portal par halka rakho
                continue

            result = parse_response(last_html)
            out = {"ok": True, "vehicle": reg_no, "attempts": attempt, **result}
            if debug:
                out["raw_preview"] = last_html[:1500]
            return out

        out = {"ok": False, "error": "captcha_failed", "vehicle": reg_no}
    except Exception as e:  # network / portal change / OCR import
        out = {"ok": False, "error": f"{type(e).__name__}: {e}", "vehicle": reg_no}

    if debug:
        out["raw_preview"] = last_html[:1500]
    return out


if __name__ == "__main__":
    import json
    import sys

    number = sys.argv[1] if len(sys.argv) > 1 else "OD02AB1234"
    print(json.dumps(check_vehicle(number, debug=True), indent=2, ensure_ascii=False))
