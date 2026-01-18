from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os

app = Flask(__name__)
CORS(app)

# ===== 10분 캐시 설정 =====
EXCHANGE_CACHE = {
    "data": None,
    "timestamp": None
}

CACHE_TTL = 600  # 10분 (초)

def get_exchange_rates_advanced():
    now = datetime.now()

    if (
        EXCHANGE_CACHE["data"] is not None
        and EXCHANGE_CACHE["timestamp"] is not None
        and (now - EXCHANGE_CACHE["timestamp"]).seconds < CACHE_TTL
    ):
        return EXCHANGE_CACHE["data"]

    try:
        url = "https://stock.mk.co.kr/"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        rates = []

        tables = soup.find_all("table")
        for table in tables:
            for row in table.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 3:
                    currency = cols[0].text.strip()
                    if any(c in currency for c in ["USD", "JPY", "EUR", "CNY", "AUD"]):
                        rates.append({
                            "currency": currency,
                            "rate": cols[1].text.strip(),
                            "change": cols[2].text.strip()
                        })

        if not rates:
            rates = get_fallback_rates()

        EXCHANGE_CACHE["data"] = rates
        EXCHANGE_CACHE["timestamp"] = now
        return rates

    except Exception:
        return get_fallback_rates()

def get_fallback_rates():
    return [
        {"currency": "USD", "rate": "1,475.5", "change": "+5.2", "flag": "🇺🇸", "name": "미국 달러"},
        {"currency": "JPY100", "rate": "933.54", "change": "+6.58", "flag": "🇯🇵", "name": "일본 엔"},
        {"currency": "EUR", "rate": "1,711.8", "change": "+4.93", "flag": "🇪🇺", "name": "유로"},
        {"currency": "CNY", "rate": "211.78", "change": "+0.63", "flag": "🇨🇳", "name": "중국 위안"},
        {"currency": "GBP", "rate": "986.37", "change": "+1.49", "flag": "🇬🇧", "name": "영국 파운드"}
    ]

def format_currency_data(rates):
    currency_map = {
        "USD": {"flag": "🇺🇸", "name": "미국 달러"},
        "JPY100": {"flag": "🇯🇵", "name": "일본 엔"},
        "EUR": {"flag": "🇪🇺", "name": "유로"},
        "CNY": {"flag": "🇨🇳", "name": "중국 위안"},
        "GBP": {"flag": "🇬🇧", "name": "영국 파운드"}
    }

    formatted = []
    for rate in rates:
        code = rate["currency"].split()[0]
        info = currency_map.get(code, {"flag": "", "name": code})

        formatted.append({
            "currency": f"{code} ({info['name']})",
            "rate": rate["rate"],
            "change": rate["change"],
            "flag": info["flag"]
        })

    return formatted

@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    rates = format_currency_data(get_exchange_rates_advanced())

    items = []
    for rate in rates:
        icon = "▲" if "+" in rate["change"] else "▼" if "-" in rate["change"] else "━"
        value = rate["change"].replace("+", "").replace("-", "")

        items.append({
            "title": f"{rate['flag']} {rate['currency']}",
            "description": f"{rate['rate']}  {icon} {value}"
        })

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "listCard": {
                        "header": {
                            "title": "이 시각 환율 (매일경제)"
                        },
                        "items": items[:5],
                        "buttons": [
                            {
                                "action": "webLink",
                                "label": "매일경제 마켓",
                                "webLinkUrl": "https://stock.mk.co.kr/"
                            }
                        ]
                    }
                },
                {
                    "simpleText": {
                        "text": f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }
                }
            ]
        }
    }

    return jsonify(response)

# ✅ 서버 깨우기 / 헬스체크용
@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
