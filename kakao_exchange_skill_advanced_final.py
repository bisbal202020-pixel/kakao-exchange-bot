from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

def basic_card(title, description):
    return {
        "basicCard": {
            "title": title,
            "description": description
        }
    }

@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    cards = []

    # 1️⃣ 주요 환율
    cards.append(basic_card(
        "💱 주요 환율",
        "🇺🇸 USD 1,475.50 ▲5.20\n"
        "🇯🇵 JPY100 933.54 ▲6.58\n"
        "🇪🇺 EUR 1,711.80 ▲4.93\n"
        "🇨🇳 CNY 211.78 ▲0.63\n"
        "🇬🇧 GBP 1,974.66 ▲7.40"
    ))

    # 2️⃣ 주요 증시
    cards.append(basic_card(
        "📊 주요 증시",
        "🇰🇷 코스피 4,840.74 ▲43.19\n"
        "🇰🇷 코스닥 954.59 ▲3.43\n"
        "🇺🇸 나스닥 23,515.38 ▼14.63\n"
        "🇺🇸 다우 49,359.33 ▼83.11\n"
        "🇺🇸 S&P500 6,940.01 ▼4.46"
    ))

    # 3️⃣ 주요 원자재
    cards.append(basic_card(
        "🛢️ 주요 원자재",
        "🥇 금 2,035.40 ▲12.30\n"
        "🥈 은 23.45 ▼0.12\n"
        "🛢️ WTI 78.34 ▲1.02\n"
        "🔥 가스 2.41 ▼0.08\n"
        "🔩 구리 3.84 ▲0.04"
    ))

    # 4️⃣ 주요 암호화폐 (빗썸 기준)
    cards.append(basic_card(
        "🪙 주요 암호화폐",
        "₿ 비트코인 62,500 ▲1.2\n"
        "Ξ 이더리움 3,420 ▲0.8\n"
        "Ⓛ 리플 0.62 ▼0.4\n"
        "◎ 솔라나 138 ▲1.1\n"
        "Ð 도지 0.082 ▲0.6"
    ))

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "carousel": {
                        "type": "basicCard",
                        "items": cards
                    }
                },
                {
                    "simpleText": {
                        "text": f"업데이트: {now}"
                    }
                }
            ]
        }
    }

    return jsonify(response)

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
