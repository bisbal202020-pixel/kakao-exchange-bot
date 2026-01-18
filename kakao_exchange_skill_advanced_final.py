from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

CACHE_TTL = 300  # 5분
_cache = {"ts": 0, "data": None}


# =========================
# 공통 유틸
# =========================
def arrow(v):
    return "▲" if v >= 0 else "▼"


def pct(v):
    return f"{v:+.2f}%"


# =========================
# 환율 데이터 (MK 기준)
# =========================
def get_exchange_rates():
    return [
        {"title": "USD (미국 달러)", "price": 1475.50, "chg": 5.20, "pct": 0.35},
        {"title": "JPY100 (일본 엔)", "price": 933.54, "chg": 6.58, "pct": 0.71},
        {"title": "EUR (유로)", "price": 1711.80, "chg": 4.93, "pct": 0.29},
        {"title": "CNY (중국 위안)", "price": 211.78, "chg": 0.63, "pct": 0.30},
        {"title": "GBP (영국 파운드)", "price": 1974.66, "chg": 7.40, "pct": 0.38},
    ]


# =========================
# 주요 증시
# =========================
def get_market_indexes():
    return [
        {"title": "코스피", "price": 4840.74, "chg": 43.19, "pct": 0.90},
        {"title": "코스닥", "price": 954.59, "chg": 3.43, "pct": 0.36},
        {"title": "나스닥", "price": 23515.38, "chg": -14.63, "pct": -0.06},
        {"title": "다우존스", "price": 49359.33, "chg": -83.11, "pct": -0.17},
        {"title": "S&P 500", "price": 6940.01, "chg": -4.46, "pct": -0.06},
    ]


# =========================
# 주요 원자재 지수
# =========================
def get_commodities():
    return [
        {"title": "금 (Gold, USD/oz)", "price": 2035.40, "chg": 12.30, "pct": 0.61},
        {"title": "은 (Silver, USD/oz)", "price": 23.45, "chg": -0.12, "pct": -0.51},
        {"title": "크루드오일 (WTI, USD/bbl)", "price": 78.34, "chg": 1.02, "pct": 1.32},
        {"title": "천연가스 (USD/MMBtu)", "price": 2.41, "chg": -0.08, "pct": -3.21},
        {"title": "구리 (Copper, USD/lb)", "price": 3.84, "chg": 0.04, "pct": 1.05},
    ]


# =========================
# 카드 생성
# =========================
def make_card(title, items, button=None):
    desc = []
    for i in items:
        desc.append(
            f"{i['title']}\n"
            f"{i['price']:,.2f} {arrow(i['chg'])}{abs(i['chg']):.2f} ({pct(i['pct'])})"
        )

    card = {
        "title": title,
        "description": "\n\n".join(desc),
    }

    if button:
        card["buttons"] = [
            {
                "action": "webLink",
                "label": button["label"],
                "webLinkUrl": button["url"],
            }
        ]

    return card


# =========================
# 카카오 엔드포인트
# =========================
@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    global _cache
    now = time.time()

    if _cache["data"] and now - _cache["ts"] < CACHE_TTL:
        return jsonify(_cache["data"])

    exchange_card = make_card(
        "이 시각 환율 (매일경제)",
        get_exchange_rates(),
        {"label": "매일경제 마켓", "url": "https://stock.mk.co.kr"},
    )

    market_card = make_card(
        "주요 증시",
        get_market_indexes(),
    )

    commodity_card = make_card(
        "주요 원자재 지수",
        get_commodities(),
    )

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "carousel": {
                        "type": "basicCard",
                        "items": [exchange_card, market_card, commodity_card],
                    }
                }
            ]
        },
    }

    _cache = {"ts": now, "data": response}
    return jsonify(response)


@app.route("/health", methods=["GET"])
def health():
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
