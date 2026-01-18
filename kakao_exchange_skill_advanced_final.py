from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

# =========================
# 캐시 설정 (5분)
# =========================
CACHE_TTL = 300
CACHE = {
    "timestamp": None,
    "exchange": None,
    "index": None
}

# =========================
# 유틸
# =========================
def is_cache_valid():
    return CACHE["timestamp"] and datetime.now() - CACHE["timestamp"] < timedelta(seconds=CACHE_TTL)

def arrow(val):
    try:
        v = float(val)
        return "▲" if v > 0 else "▼" if v < 0 else "-"
    except:
        return "-"

def percent(change, base):
    try:
        return round((float(change) / float(base)) * 100, 2)
    except:
        return 0.0

# =========================
# 환율 스크래핑
# =========================
def fetch_exchange_rates():
    url = "https://stock.mk.co.kr"
    res = requests.get(url, timeout=5)
    soup = BeautifulSoup(res.text, "html.parser")

    mapping = {
        "미국": ("USD", "미국 달러", "🇺🇸"),
        "일본": ("JPY100", "일본 엔", "🇯🇵"),
        "유로": ("EUR", "유로", "🇪🇺"),
        "중국": ("CNY", "중국 위안", "🇨🇳"),
        "영국": ("GBP", "영국 파운드", "🇬🇧")
    }

    rates = []
    rows = soup.select("table tbody tr")

    for r in rows:
        cols = [c.get_text(strip=True) for c in r.find_all("td")]
        if len(cols) < 3:
            continue

        country = cols[0]
        price = cols[1].replace(",", "")
        change = cols[2].replace(",", "").replace("▲", "").replace("▼", "")

        if country in mapping:
            code, name, flag = mapping[country]
            rates.append({
                "title": f"{flag} {code} ({name})",
                "price": f"{float(price):,.2f}",
                "change": f"{arrow(change)}{abs(float(change))}",
                "percent": f"{percent(change, price):+.2f}%"
            })

    return rates

# =========================
# 지수 스크래핑
# =========================
def fetch_index_data():
    url = "https://stock.mk.co.kr"
    res = requests.get(url, timeout=5)
    soup = BeautifulSoup(res.text, "html.parser")

    mapping = {
        "코스피": "🇰🇷 KOSPI",
        "코스닥": "🇰🇷 KOSDAQ",
        "다우존스": "🇺🇸 DOW",
        "나스닥": "🇺🇸 NASDAQ",
        "S&P 500": "🇺🇸 S&P500"
    }

    indexes = []
    rows = soup.select("table tbody tr")

    for r in rows:
        cols = [c.get_text(strip=True) for c in r.find_all("td")]
        if len(cols) < 3:
            continue

        name = cols[0]
        price = cols[1].replace(",", "")
        change = cols[2].replace(",", "").replace("▲", "").replace("▼", "")

        if name in mapping:
            indexes.append({
                "title": mapping[name],
                "price": f"{float(price):,.2f}",
                "change": f"{arrow(change)}{abs(float(change))}",
                "percent": f"{percent(change, price):+.2f}%"
            })

    return indexes

# =========================
# 메인 엔드포인트
# =========================
@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    global CACHE

    if is_cache_valid():
        exchange = CACHE["exchange"]
        index = CACHE["index"]
    else:
        exchange = fetch_exchange_rates()
        index = fetch_index_data()
        CACHE["exchange"] = exchange
        CACHE["index"] = index
        CACHE["timestamp"] = datetime.now()

    carousel = []

    # 환율 카드
    carousel.append({
        "basicCard": {
            "title": "이 시각 환율 (매일경제)",
            "description": "",
            "thumbnail": {"imageUrl": ""},
            "items": [
                {"title": r["title"], "description": f'{r["price"]} {r["change"]} ({r["percent"]})'}
                for r in exchange
            ],
            "buttons": [
                {
                    "action": "webLink",
                    "label": "매일경제 마켓",
                    "webLinkUrl": "https://stock.mk.co.kr"
                }
            ]
        }
    })

    # 지수 카드
    carousel.append({
        "basicCard": {
            "title": "주요 증시 지수",
            "description": "",
            "thumbnail": {"imageUrl": ""},
            "items": [
                {"title": i["title"], "description": f'{i["price"]} {i["change"]} ({i["percent"]})'}
                for i in index
            ]
        }
    })

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {"carousel": {"type": "basicCard", "items": carousel}}
            ]
        }
    })

# =========================
# 헬스체크
# =========================
@app.route("/health")
def health():
    return "ok", 200

# =========================
# 실행
# =========================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
