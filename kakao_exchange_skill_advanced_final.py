from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =====================
# Helper
# =====================

def arrow(diff):
    return "🔺" if diff > 0 else "🔻"

def basic_card(title, description):
    return {
        "basicCard": {
            "title": title,
            "description": description
        }
    }

def carousel(cards):
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "carousel": {
                    "type": "basicCard",
                    "items": cards
                }
            }]
        }
    }

# =====================
# Route
# =====================

@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    # 실데이터는 기존 로직 그대로 써도 됨
    fx = [
        f"🇺🇸 USD 1,475.5 {arrow(1)} 5.2",
        f"🇯🇵 JPY 933.5 {arrow(1)} 6.5",
        f"🇪🇺 EUR 1,711.8 {arrow(1)} 4.9",
        f"🇨🇳 CNY 211.7 {arrow(1)} 0.6",
        f"🇬🇧 GBP 1,974.6 {arrow(1)} 7.4",
    ]

    indices = [
        f"🇰🇷 코스피 4,840.7 {arrow(1)} 43.1",
        f"🇰🇷 코스닥 954.6 {arrow(1)} 3.4",
        f"🇺🇸 나스닥 23,515 {arrow(-1)} 14.6",
        f"🇺🇸 다우 49,359 {arrow(-1)} 83.1",
        f"🇺🇸 S&P500 6,940 {arrow(-1)} 4.4",
    ]

    commodities = [
        f"🥇 금 2,035 {arrow(1)} 12.3",
        f"🥈 은 23.4 {arrow(-1)} 0.1",
        f"🛢 WTI 78.3 {arrow(1)} 1.0",
        f"🔥 가스 2.4 {arrow(-1)} 0.1",
        f"🔩 구리 3.8 {arrow(1)} 0.0",
    ]

    crypto = [
        f"₿ BTC 62,500 {arrow(1)}",
        f"Ξ ETH 3,420 {arrow(1)}",
        f"✕ XRP 0.62 {arrow(1)}",
        f"◎ SOL 138 {arrow(1)}",
        f"Ð DOGE 0.082 {arrow(1)}",
    ]

    cards = [
        basic_card("1. 주요 환율", "\n".join(fx)),
        basic_card("2. 주요 증시", "\n".join(indices)),
        basic_card("3. 주요 원자재", "\n".join(commodities)),
        basic_card("4. 주요 암호화폐", "\n".join(crypto)),
    ]

    return jsonify(carousel(cards))


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
