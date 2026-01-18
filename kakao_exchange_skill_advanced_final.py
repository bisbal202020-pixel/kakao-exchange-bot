from flask import Flask, request, jsonify
import time
from datetime import datetime

app = Flask(__name__)

# =====================
# 캐시 설정
# =====================
CACHE_TTL = 300  # 5분
cache = {
    "rates": {"data": None, "ts": 0, "updated_at": None},
    "indices": {"data": None, "ts": 0, "updated_at": None}
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
# 환율 데이터
# =====================
def get_exchange_rates():
    now = time.time()
    if cache["rates"]["data"] and now - cache["rates"]["ts"] < CACHE_TTL:
        return cache["rates"]

    data = [
        {"code": "USD", "name": "미국 달러", "value": 1475.50, "chg": 5.20, "pct": 0.35, "flag": "🇺🇸"},
        {"code": "JPY100", "name": "일본 엔", "value": 933.54, "chg": 6.58, "pct": 0.71, "flag": "🇯🇵"},
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
# 지수 데이터
# =====================
def get_indices():
    now = time.time()
    if cache["indices"]["data"] and now - cache["indices"]["ts"] < CACHE_TTL:
        return cache["indices"]

    data = [
        {"name": "코스피", "value": 4840.74, "chg": 43.19, "pct": 0.90},
        {"name": "코스닥", "value": 954.59, "chg": 3.43, "pct": 0.36},
        {"name": "나스닥", "value": 23515.38, "chg": -14.63, "pct": -0.06},
        {"name": "다우존스", "value": 49359.33, "chg": -83.11, "pct": -0.17},
        {"name": "S&P 500", "value": 6940.01, "chg": -4.46, "pct": -0.06},
    ]

    cache["indices"] = {
        "data": data,
        "ts": now,
        "updated_at": now_kst()
    }
    return cache["indices"]

# =====================
# 카드 포맷
# =====================
def build_exchange_card(rates_cache):
    items = []
    for r in rates_cache["data"]:
        items.append({
            "title": f"{r['flag']} {r['code']} ({r['name']})",
            "description": f"{r['value']:,.2f} {arrow(r['chg'])}{abs(r['chg'])} ({sign(r['pct'])}%)"
        })

    return {
        "header": {
            "title": f"고시 환율 ({rates_cache['updated_at']} 기준)"
        },
        "items": items,
        "buttons": [{
            "label": "매일경제 마켓",
            "action": "webLink",
            "webLinkUrl": "https://stock.mk.co.kr/"
        }]
    }

def build_index_card(indices_cache):
    items = []
    for i in indices_cache["data"]:
        items.append({
            "title": i["name"],
            "description": f"{i['value']:,.2f} {arrow(i['chg'])}{abs(i['chg'])} ({sign(i['pct'])}%)"
        })

    return {
        "header": {
            "title": f"주요 증시 ({indices_cache['updated_at']} 기준)"
        },
        "items": items
    }

# =====================
# 카카오 스킬 엔드포인트
# =====================
@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    rates_cache = get_exchange_rates()
    indices_cache = get_indices()

    response = {
        "version": "2.0",
        "template": {
            "outputs": [{
                "carousel": {
                    "type": "listCard",
                    "items": [
                        build_exchange_card(rates_cache),
                        build_index_card(indices_cache)
                    ]
                }
            }]
        }
    }
    return jsonify(response)

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
