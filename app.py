"""
app.py - Vehicle document check (Step 1)

Endpoints:
  GET /              -> chhota status message
  GET /health        -> Render health check
  GET /check?no=OD02AB1234[&debug=1][&key=SECRET]

Render / GitHub auto-deploy:
  Start command:  gunicorn app:app --timeout 90 --workers 1
  Env vars (optional):
    API_KEY  -> set karoge to /check par ?key=... ya header X-API-Key zaroori ho jayega
                (public link par koi bhi use na kar sake, isliye recommended)
"""

import hmac
import os

from flask import Flask, jsonify, request

from scraper import check_vehicle, normalize_reg_no

app = Flask(__name__)
app.json.ensure_ascii = False  # emoji / Hindi sahi dikhe

API_KEY = os.environ.get("API_KEY", "").strip()


def _authorized() -> bool:
    """API_KEY set nahi hai to open (sirf testing ke liye)."""
    if not API_KEY:
        return True
    given = request.headers.get("X-API-Key") or request.args.get("key", "")
    return hmac.compare_digest(given.encode(), API_KEY.encode())


@app.get("/")
def home():
    return jsonify({"service": "vehicle-doc-check", "status": "running"})


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/check")
def check():
    if not _authorized():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    number = normalize_reg_no(request.args.get("no", ""))
    if not number:
        return jsonify({"ok": False, "error": "missing ?no=VEHICLE_NUMBER"}), 400

    debug = request.args.get("debug") == "1"
    result = check_vehicle(number, debug=debug)

    if result.get("ok"):
        code = 200
    elif result.get("error") == "invalid_vehicle_number":
        code = 400
    else:
        code = 502  # portal / captcha problem
    return jsonify(result), code


if __name__ == "__main__":
    # Local test only. Render par gunicorn chalega.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
