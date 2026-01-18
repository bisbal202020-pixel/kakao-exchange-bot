from flask import Flask, request, jsonify
import time

app = Flask(__name__)

CACHE_TTL = 300
_cache = {"ts": 0, "data": None}


def arrow(v):
    return "▲" if v >= 0 else "▼"


def pct(v):
    return f"{v:+.2f}%"


def basic_card(title, items):
    lines = []
    for i in items:
        lines.append(
            f"{i['title']}\n"
            f"{i['price']:,.2f} {arrow(i['chg'])}{abs(i['chg']):.2f} ({pct(i['pct'])})"
        )
    return {
        "title": title,
        "description": "\n\n".join(lines)
    }


def list_card(title, items):
    return {
        "header": {"title": title},
        "items": [
            {
                "title": i["title"],
                "description": f"{i['price']:,.2f} {arrow(i['chg'])}{abs(i['chg']):.2f} ({pct(i['pct'])})"
            }
            for i in items
        ]
    }


@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    global _cache
    now = time.time()

    if _cache["data"] and now - _cache["ts"] < CACHE_TTL:
        return jsonify(_cache["data"])

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "carousel": {
                        "type": "basicCard",
                        "items": [
                            basic_card(
                                "이 시각 환율 (매일경제)",
                                [
                                    {"title": "USD (미국 달러)", "price": 1475.50, "chg": 5.20, "pct": 0.35},
                                    {"title": "JPY100 (일본 엔)", "price": 933.54, "chg": 6.58, "pct": 0.71},
                                    {"title": "EUR (유로)", "price": 1711.80, "chg": 4.93, "pct": 0.29},
                                    {"title": "CNY (중국 위안)", "price": 211.78, "chg": 0.63, "pct": 0.30},
                                    {"title": "GBP (영국 파운드)", "price": 1974.66, "chg": 7.40, "pct": 0.38},
                                ]
                            ),
                            basic_card(
                                "주요 증시",
                                [
                                    {"title": "코스피", "price": 4840.74, "chg": 43.19, "pct": 0.90},
                                    {"title": "코스닥", "price": 954.59, "chg": 3.43, "pct": 0.36},
                                    {"title": "나스닥", "price": 23515.38, "chg": -14.63, "pct": -0.06},
                                    {"title": "다우존스", "price": 49359.33, "chg": -83.11, "pct": -0.17},
                                    {"title": "S&P 500", "price": 6940.01, "chg": -4.46, "pct": -0.06},
                                ]
                            ),
                        ]
                    }
                },
                {
                    "listCard": list_card(
                        "주요 원자재 지수",
                        [
                            {"title": "금 (USD/oz)", "price": 2035.40, "chg": 12.30, "pct": 0.61},
                            {"title": "은 (USD/oz)", "price": 23.45, "chg": -0.12, "pct": -0.51},
                            {"title": "크루드오일 (WTI, USD/bbl)", "price": 78.34, "chg": 1.02, "pct": 1.32},
                            {"title": "천연가스 (USD/MMBtu)", "price": 2.41, "chg": -0.08, "pct": -3.21},
                            {"title": "구리 (USD/lb)", "price": 3.84, "chg": 0.04, "pct": 1.05},
                        ]
                    )
                }
            ]
        }
    }

    _cache = {"ts": now, "data": response}
    return jsonify(response)


@app.route("/health", methods=["GET"])
def health():
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
