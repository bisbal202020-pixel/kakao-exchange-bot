from flask import Flask, jsonify
import requests
import time
from datetime import datetime, time as dtime, date
from zoneinfo import ZoneInfo

app = Flask(__name__)

# =====================
# 캐시 (해외지수용)
# =====================
CACHE_TTL = 300
cache = {
    "us_indices": {"data": None, "ts": 0, "updated_at": None}
}

# =====================
# 유틸
# =====================
def arrow(val):
    return "▲" if val >= 0 else "▼"

def sign(val):
    return f"+{val}" if val > 0 else f"{val}"

def now_kst():
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y.%m.%d %H:%M")

def now_kst_dt():
    return datetime.now(ZoneInfo("Asia/Seoul"))

# =====================
# 🇰🇷 공휴일 (연 1회 관리)
# =====================
KR_HOLIDAYS = {
    date(2026, 1, 1),
    date(2026, 2, 16),
    date(2026, 3, 1),
    date(2026, 5, 5),
    date(2026, 6, 6),
    date(2026, 8, 15),
    date(2026, 9, 28),
    date(2026, 9, 29),
    date(2026, 9, 30),
    date(2026, 10, 3),
    date(2026, 10, 9),
    date(2026, 12, 25),
}

# =====================
# 🇰🇷 장 상태 (KST 기준)
# =====================
def get_kr_market_status():
    now = now_kst_dt()
    today = now.date()
    t = now.time()

    if today.weekday() >= 5 or today in KR_HOLIDAYS:
        return "휴장"

    if dtime(9, 0) <= t <= dtime(15, 30):
        return "개장 중"

    return "장 마감"

# =====================
# 🇰🇷 Yahoo Finance 실시간 지수
# =====================
def fetch_yahoo_index(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "interval": "1m",
        "range": "1d"
    }

    r = requests.get(url, params=params, timeout=2)
    j = r.json()

    meta = j["chart"]["result"][0]["meta"]
    price = meta["regularMarketPrice"]
    prev = meta["previousClose"]

    chg = price - prev
    pct = (chg / prev) * 100

    return round(price, 2), round(chg, 2), round(pct, 2)

# =====================
# 🇰🇷 국내 지수 (호출 시마다 실시간)
# =====================
def get_kr_indices():
    status = get_kr_market_status()

    kospi_v, kospi_c, kospi_p = fetch_yahoo_index("^KS11")
    kosdaq_v, kosdaq_c, kosdaq_p = fetch_yahoo_index("^KQ11")

    return {
        "status": status,
        "data": [
            {"name": "코스피", "value": kospi_v, "chg": kospi_c, "pct": kospi_p},
            {"name": "코스닥", "value": kosdaq_v, "chg": kosdaq_c, "pct": kosdaq_p},
        ],
        "updated_at": now_kst()
    }

# =====================
# 🇺🇸 해외 지수 (전일 종가, 캐시)
# =====================
def get_us_indices():
    now = time.time()
    if cache["us_indices"]["data"] and now - cache["us_indices"]["ts"] < CACHE_TTL:
        return cache["us_indices"]

    data = [
        {"name": "나스닥", "value": 23515.38, "chg": -14.63, "pct": -0.06},
        {"name": "다우존스", "value": 49359.33, "chg": -83.11, "pct": -0.17},
        {"name": "S&P 500", "value": 6940.01, "chg": -4.46, "pct": -0.06},
    ]

    cache["us_indices"] = {
        "data": data,
        "ts": now,
        "updated_at": now_kst()
    }
    return cache["us_indices"]

# =====================
# 카드 빌드
# =====================
def build_index_card(kr, us):
    items = []

    for i in kr["data"]:
        items.append({
            "title": f"{i['name']} ({kr['status']})",
            "description": f"{i['value']:,.2f} {arrow(i['chg'])}{abs(i['chg'])} ({sign(i['pct'])}%)"
        })

    for i in us["data"]:
        items.append({
            "title": f"{i['name']} (전일 종가)",
            "description": f"{i['value']:,.2f} {arrow(i['chg'])}{abs(i['chg'])} ({sign(i['pct'])}%)"
        })

    return {
        "header": {
            "title": f"주요 증시 ({kr['updated_at']} 기준)"
        },
        "items": items
    }

# =====================
# 카카오 스킬
# =====================
@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    kr = get_kr_indices()
    us = get_us_indices()

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "carousel": {
                    "type": "listCard",
                    "items": [
                        build_index_card(kr, us)
                    ]
                }
            }]
        }
    })

@app.route("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
