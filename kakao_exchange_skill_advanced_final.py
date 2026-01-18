from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# =========================
# 캐시 설정 (5분)
# =========================
CACHE_TTL = timedelta(minutes=5)
CACHE = {
    "exchange": {"data": None, "time": None},
    "indices": {"data": None, "time": None},
}

# =========================
# 유틸
# =========================
def is_cache_valid(cache):
    return cache["data"] and cache["time"] and datetime.now() - cache["time"] < CACHE_TTL


def arrow(change):
    try:
        return "▲" if float(change) > 0 else "▼"
    except:
        return ""


# =========================
# 환율 스크래핑
# =========================
def fetch_exchange():
    if is_cache_valid(CACHE["exchange"]):
        return CACHE["exchange"]["data"]

    url = "https://stock.mk.co.kr"
    soup = BeautifulSoup(requests.get(url, timeout=5).text, "html.parser")

    rows = soup.select("table tbody tr")
    result = []

    for row in rows:
        cols = row.select("td")
        if len(cols) < 3:
            continue

        name = cols[0].get_text(strip=True)
        price = cols[1].get_text(strip=True).replace(",", "")
        change = cols[2].get_text(strip=True)

        if "미국" in name:
            code = "USD"
            flag = "🇺🇸"
            label = "미국 달러"
        elif "일본" in name:
            code = "JPY100"
            flag = "🇯🇵"
            label = "일본 엔"
        elif "유로" in name:
            code = "EUR"
            flag = "🇪🇺"
            label = "유로"
        elif "중국" in name:
            code = "CNY"
            flag = "🇨🇳"
            label = "중국 위안"
        elif "영국" in name:
            code = "GBP"
            flag = "🇬🇧"
            label = "영국 파운드"
        else:
            continue

        pct = ""
        if "(" in change:
            pct = change[change.find("("):]

        result.append({
            "title": f"{flag} {code} ({label})",
            "price": f"{float(price):,.2f}",
            "change": f"{arrow(change)}{change.split('(')[0].strip()}",
            "percent": pct
        })

    CACHE["exchange"] = {"data": result, "time": datetime.now()}
    return result


# =========================
# 지수 스크래핑
# =========================
def fetch_indices():
    if is_cache_valid(CACHE["indices"]):
        return CACHE["indices"]["data"]

    url = "https://stock.mk.co.kr"
    soup = BeautifulSoup(requests.get(url, timeout=5).text, "html.parser")

    rows = soup.select("div.marketIndex table tbody tr")
    result = []

    for row in rows:
        cols = row.select("td")
        if len(cols) < 3:
            continue

        name = cols[0].get_text(strip=True)
        price = cols[1].get_text(strip=True)
        change = cols[2].get_text(strip=True)

        if name in ["코스피", "코스닥", "나스닥", "다우존스", "S&P 500"]:
            pct = ""
            if "(" in change:
                pct = change[change.find("("):]

            result.append({
                "title": name,
                "price": price,
                "change": f"{arrow(change)}{change.split('(')[0].strip()}",
                "percent": pct
            })

    CACHE["indices"] = {"data": result, "time": datetime.now()}
    return result


# =========================
# 카카오 응답
# =========================
@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    exchange = fetch_exchange()
    indices = fetch_indices()

    cards = []

    # 환율 카드
    cards.append({
        "title": "이 시각 환율 (매일경제)",
        "description": "",
        "items": [
            {
                "title": r["title"],
                "description": f'{r["price"]} {r["change"]} {r["percent"]}'
            }
            for r in exchange
        ],
        "buttons": [
            {
                "action": "webLink",
                "label": "매일경제 마켓",
                "webLinkUrl": "https://stock.mk.co.kr"
            }
        ]
    })

    # 지수 카드
    cards.append({
        "title": "주요 증시 지수",
        "description": "",
        "items": [
            {
                "title": r["title"],
                "description": f'{r["price"]} {r["change"]} {r["percent"]}'
            }
            for r in indices
        ]
    })

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "carousel": {
                        "type": "basicCard",
                        "items": cards
                    }
                }
            ]
        }
    }

    return jsonify(response)


@app.route("/health")
def health():
    return "ok", 200


if __name__ == "__main__":
    import os
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
