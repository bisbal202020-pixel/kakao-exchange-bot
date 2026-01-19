from flask import Flask, jsonify
import requests
import time
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

app = Flask(__name__)

# =====================
# 캐시 (카카오 타임아웃 방지용)
# =====================
KR_CACHE_TTL = 30  # 30초
kr_cache = {"data": None, "ts": 0}

# =====================
# 유틸
# =====================
def arrow(val):
    return "▲" if val >= 0 else "▼"

def sign(val):
    return f"+{val}" if val > 0 else f"{val}"

def now_kst_dt():
    return datetime.now(ZoneInfo("Asia/Seoul"))

def now_kst():
    return now_kst_dt().strftime("%Y.%m.%d %H:%M")

# =====================
# 장 상태 (아주 단순)
# =====================
def get_kr_market_status():
    now = now_kst_dt().time()
    if dtime(9, 0) <= now <= dtime(15, 30):
        return "개장 중"
    return "장 마감"

# =====================
# Yahoo Finance 지수
# =====================
def fetch_yahoo_index(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1m", "range": "1d"}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    r = requests.get(url, params=params, headers=headers, timeout=2)
    j = r.json()["chart"]["result"][0]["meta"]

    price = j["regularMarketPrice"]
    prev = j["previousClose"]

    chg = price - prev
    pct = (chg / prev) * 100

    return round(price, 2), round(chg, 2), round(pct, 2)

# =====================
# 🇰🇷 국내 지수 (실시간 + 30초 캐시)
# =====================
def get_kr_indices():
    now_ts = time.time()

    if kr_cache["data"] and now_ts - kr_cache["ts"] < KR_CACHE_TTL:
        return kr_cache["data"]

    status = get_kr_market_status()

    try:
        kospi_v, kospi_c, kospi_p = fetch_yahoo_index("^KS11")
        kosdaq_v, kosdaq_c, kosdaq_p = fetch_yahoo_index("^KQ11")
    except Exception:
        # 외부 API 잠깐 죽어도 무응답 방지
        if kr_cache["data"]:
            return kr_cache["data"]
        raise

    data = {
        "status": status,
        "data": [
            {"name": "코스피", "value": kospi_v, "chg": kospi_c, "pct": kospi_p},
            {"name": "코스닥", "value": kosdaq_v, "chg": kosdaq_c, "pct": kosdaq_p},
        ],
        "updated_at": now_kst()
    }

    kr_cache["data"] = data
    kr_cache["ts"] = now_ts
    return data

# =====================
# 카드 빌드
# =====================
def build_index_card(kr):
    items = []
    for i in kr["data"]:
        items.append({
            "title": f"{i['name']} ({kr['status']})",
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

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "carousel": {
                    "type": "listCard",
                    "items": [
                        build_index_card(kr)
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
