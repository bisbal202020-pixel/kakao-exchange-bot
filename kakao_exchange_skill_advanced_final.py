from flask import Flask, jsonify
import time
from datetime import datetime, time as dtime, date

app = Flask(__name__)

# =====================
# 캐시 (해외지수/환율만)
# =====================
CACHE_TTL = 300
cache = {
    "rates": {"data": None, "ts": 0, "updated_at": None},
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
    return datetime.now().strftime("%Y.%m.%d %H:%M")

# =====================
# 🇰🇷 한국 공휴일 (연 1회 관리)
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
# 🇰🇷 장 상태 판별
# =====================
def get_kr_market_status():
    today = datetime.now().date()
    now = datetime.now().time()

    if today.weekday() >= 5:
        return "휴장"

    if today in KR_HOLIDAYS:
        return "휴장"

    if dtime(9, 0) <= now <= dtime(15, 30):
        return "개장 중"

    return "장 마감"

# =====================
# 환율 (기존 유지)
# =====================
def get_exchange_rates():
    now = time.time()
    if cache["rates"]["data"] and now - cache["rates"]["ts"] < CACHE_TTL:
        return cache["rates"]

    data = [
        {"code": "USD", "name": "미국 달러", "value": 1475.50, "chg": 5.20, "pct": 0.35, "flag": "🇺🇸"},
        {"code": "JPY", "name": "일본 엔", "value": 933.54, "chg": 6.58, "pct": 0.71, "flag": "🇯🇵"},
        {"code": "EUR", "name": "유로", "value": 1711.80, "chg": 4.93, "pct": 0.29, "flag": "🇪🇺"},
        {"code": "CNY", "name": "중국 위안", "value": 211.78, "chg": 0.63, "pct": 0.30, "flag": "🇨🇳"},
        {"code": "GBP", "name": "영국 파운드", "value": 1974.66, "chg": 7.40, "pct": 0.38, "flag": "🇬🇧"},
    ]

    cache["rates"] = {
        "data": data,
        "ts": now,
        "updated_at": now_kst()
    }
    return cache["rates"]

# =====================
# 🇰🇷 국내 지수 (실시간, 캐시 ❌)
# =====================
def get_kr_indices():
    status = get_kr_market_status()

    return {
        "status": status,
        "data": [
            {"name": "코스피", "value": 4840.74, "chg": 43.19, "pct": 0.90},
            {"name": "코스닥", "value": 954.59, "chg": 3.43, "pct": 0.36},
        ],
        "updated_at": now_kst()
    }

# =====================
# 🇺🇸 해외 지수 (전일 종가, 캐시 ⭕)
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

def build_exchange_card(rates):
    items = []
    for r in rates["data"]:
        items.append({
            "title": f"{r['flag']} {r['code']} ({r['name']})",
            "description": f"{r['value']:,.2f} {arrow(r['chg'])}{abs(r['chg'])} ({sign(r['pct'])}%)"
        })

    return {
        "header": {
            "title": f"고시 환율 ({rates['updated_at']} 기준)"
        },
        "items": items
    }

# =====================
# 카카오 스킬
# =====================
@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    rates = get_exchange_rates()
    kr = get_kr_indices()
    us = get_us_indices()

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "carousel": {
                    "type": "listCard",
                    "items": [
                        build_exchange_card(rates),
                        build_index_card(kr, us)
                    ]
                }
            }]
        }
    })

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
