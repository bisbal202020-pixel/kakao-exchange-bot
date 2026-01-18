from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# ===== 캐시 설정 =====
EXCHANGE_CACHE = {"data": None, "timestamp": None}
CACHE_TTL = 600  # 10분

TARGET_ROWS = {
    "미국":  {"code": "USD",   "flag": "🇺🇸", "name": "미국 달러"},
    "일본":  {"code": "JPY100","flag": "🇯🇵", "name": "일본 엔"},
    "유로":  {"code": "EUR",   "flag": "🇪🇺", "name": "유로"},
    "중국":  {"code": "CNY",   "flag": "🇨🇳", "name": "중국 위안"},
    "영국":  {"code": "GBP",   "flag": "🇬🇧", "name": "영국 파운드"},
}

def _clean(text):
    return (text or "").strip()

def _clean_change(text):
    t = _clean(text)
    t = t.replace("▲", "+").replace("△", "+").replace("▼", "-").replace("▽", "-")
    t = t.replace(" ", "")
    return t

def get_exchange_rates_advanced():
    now = datetime.now()

    if (
        EXCHANGE_CACHE["data"]
        and EXCHANGE_CACHE["timestamp"]
        and (now - EXCHANGE_CACHE["timestamp"]).seconds < CACHE_TTL
    ):
        return EXCHANGE_CACHE["data"]

    try:
        r = requests.get(
            "https://stock.mk.co.kr/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        found = {}

        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            col0 = tds[0].get_text(" ", strip=True)
            rate = _clean(tds[1].get_text())
            change = _clean_change(tds[2].get_text())

            for key, meta in TARGET_ROWS.items():
                if key in col0 and key not in found and rate:
                    found[key] = {
                        "currency": meta["code"],
                        "rate": rate,
                        "change": change or "0",
                        "flag": meta["flag"],
                        "name": meta["name"],
                    }

        rates = [found[k] for k in ["미국", "일본", "유로", "중국", "영국"] if k in found]
        if len(rates) < 5:
            rates = get_fallback_rates()

        EXCHANGE_CACHE["data"] = rates
        EXCHANGE_CACHE["timestamp"] = now
        return rates

    except Exception:
        return get_fallback_rates()

def get_fallback_rates():
    return [
        {"currency": "USD", "rate": "1,475.50", "change": "+5.20", "flag": "🇺🇸", "name": "미국 달러"},
        {"currency": "JPY100", "rate": "933.54", "change": "+6.58", "flag": "🇯🇵", "name": "일본 엔"},
        {"currency": "EUR", "rate": "1,711.80", "change": "+4.93", "flag": "🇪🇺", "name": "유로"},
        {"currency": "CNY", "rate": "211.78", "change": "+0.63", "flag": "🇨🇳", "name": "중국 위안"},
        {"currency": "GBP", "rate": "1,974.66", "change": "+7.40", "flag": "🇬🇧", "name": "영국 파운드"},
    ]

def format_currency_data(rates):
    formatted = []

    for rate in rates:
        raw = rate.get("change", "0")

        try:
            value = abs(float(raw.replace("+", "").replace("-", "")))
        except:
            value = 0.0

        arrow = "▲" if raw.startswith("+") else "▼" if raw.startswith("-") else "━"

        formatted.append({
            "currency": f"{rate['currency']} ({rate['name']})",
            "rate": rate["rate"],
            "change": f"{arrow} {value}",
            "flag": rate["flag"]
        })

    return formatted

@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    rates = format_currency_data(get_exchange_rates_advanced())

    items = [{
        "title": f"{r['flag']} {r['currency']}",
        "description": f"{r['rate']}  {r['change']}"
    } for r in rates]

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "listCard": {
                        "header": {"title": "이 시각 환율 (매일경제)"},
                        "items": items,
                        "buttons": [{
                            "action": "webLink",
                            "label": "매일경제 마켓",
                            "webLinkUrl": "https://stock.mk.co.kr/"
                        }]
                    }
                },
                {
                    "simpleText": {
                        "text": f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }
                }
            ]
        }
    })

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
