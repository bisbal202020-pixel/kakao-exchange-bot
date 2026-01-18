from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

def basic_card(title, desc):
    return {
        "title": title,
        "description": desc
    }

@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    cards = []

    # 1️⃣ 주요 환율
    cards.append(basic_card(
        "💱 주요 환율",
        "🇺🇸 USD 1,475.5 ▲5.2\n"
        "🇯🇵 JPY100 933.5 ▲6.5\n"
        "🇪🇺 EUR 1,711.8 ▲4.9\n"
        "🇨🇳 CNY 211.7 ▲0.6\n"
        "🇬🇧 GBP 1,974.6 ▲7.4"
    ))

    # 2️⃣ 주요 증시
    cards.append(basic_card(
        "📈 주요 증시",
        "코스피 4,840 ▲43\n"
        "코스닥 954 ▲3\n"
        "나스닥 23,515 ▼14\n"
        "다우 49,359 ▼83\n"
        "S&P500 6,940 ▼4"
    ))

    # 3️⃣ 주요 원자재
    cards.append(basic_card(
        "⛏ 주요 원자재",
        "금 2,035 ▲12\n"
        "은 23.4 ▼0.1\n"
        "WTI 78.3 ▲1.0\n"
        "가스 2.4 ▼0.0\n"
        "구리 3.8 ▲0.0"
    ))

    # 4️⃣ 주요 암호화폐 (빗썸 기준)
    cards.append(basic_card(
        "🪙 주요 암호화폐",
        "비트코인 62,500 ▲1.2\n"
        "이더리움 3,420 ▲0.8\n"
        "리플 0.62 ▲0.0\n"
        "솔라나 138 ▲1.1\n"
        "도지 0.082 ▲0.0"
    ))

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "carousel": {
                        "type": "basicCard",
                        "items": cards
                    }
                }
            ]
        }
    })

@app.route("/health", methods=["HEAD", "GET"])
def health():
    return "", 200
