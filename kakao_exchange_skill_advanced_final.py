from flask import Flask, jsonify
import requests
import time

app = Flask(__name__)

CACHE = {}
CACHE_TTL = 300  # 5분

# -------------------------
# 공통 캐시 함수
# -------------------------
def get_cached(key, fetcher):
    now = time.time()
    if key in CACHE and now - CACHE[key]["ts"] < CACHE_TTL:
        return CACHE[key]["data"]
    data = fetcher()
    CACHE[key] = {"data": data, "ts": now}
    return data

# -------------------------
# 환율 (예시: 기존 로직 유지)
# -------------------------
def fetch_fx():
    return [
        "USD 1475.5 ▲5.2",
        "JPY 933.5 ▲6.6",
        "EUR 1711.8 ▲4.9",
        "CNY 211.8 ▲0.6",
        "GBP 1974.7 ▲7.4",
    ]

# -------------------------
# 증시
# -------------------------
def fetch_index():
    return [
        "코스피 4840.7 ▲43.1",
        "코스닥 954.6 ▲3.4",
        "나스닥 23515 ▼14.6",
        "다우 49359 ▼83.1",
        "S&P500 6940 ▼4.4",
    ]

# -------------------------
# 원자재
# -------------------------
def fetch_commodities():
    return [
        "금 2035 ▲12.3",
        "은 23.45 ▼0.12",
        "WTI 78.3 ▲1.0",
        "가스 2.41 ▼0.08",
        "구리 3.84 ▲0.04",
    ]

# -------------------------
# 암호화폐 (빗썸 기준)
# -------------------------
def fetch_crypto():
    try:
        r = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=3).json()
        data = r["data"]
        return [
            f"BTC {int(float(data['BTC']['closing_price']))}",
            f"ETH {int(float(data['ETH']['closing_price']))}",
            f"XRP {float(data['XRP']['closing_price']):.1f}",
            f"ADA {float(data['ADA']['closing_price']):.1f}",
            f"SOL {float(data['SOL']['closing_price']):.1f}",
        ]
    except:
        return [
            "BTC -",
            "ETH -",
            "XRP -",
            "ADA -",
            "SOL -",
        ]

# -------------------------
# 카카오 응답
# -------------------------
@app.route("/exchange", methods=["POST"])
def exchange():
    fx = get_cached("fx", fetch_fx)
    idx = get_cached("idx", fetch_index)
    cmd = get_cached("cmd", fetch_commodities)
    cry = get_cached("cry", fetch_crypto)

    def card(title, lines):
        return {
            "basicCard": {
                "title": title,
                "description": "\n".join(lines)
            }
        }

    response = {
        "version": "2.0",
        "template": {
            "outputs": [{
                "carousel": {
                    "type": "basicCard",
                    "items": [
                        card("주요 환율", fx),
                        card("주요 증시", idx),
                        card("주요 원자재", cmd),
                        card("주요 암호화폐", cry),
                    ]
                }
            }]
        }
    }

    return jsonify(response)

# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
