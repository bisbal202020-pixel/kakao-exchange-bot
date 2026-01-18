from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

# =========================
# 공통 유틸
# =========================
def arrow(value):
    try:
        v = float(value)
        return "▲" if v >= 0 else "▼"
    except:
        return ""

def fmt(num, d=2):
    try:
        return f"{float(num):,.{d}f}"
    except:
        return "-"

# =========================
# 1. 주요 환율 (예시 API 구조)
# =========================
def get_fx():
    # 실제 사용 중인 환율 API 로직 유지 전제
    return [
        ("USD", 1475.50, 5.20),
        ("JPY100", 933.54, 6.58),
        ("EUR", 1711.80, 4.93),
        ("CNY", 211.78, 0.63),
        ("GBP", 1974.66, 7.40),
    ]

# =========================
# 2. 주요 증시
# =========================
def get_indices():
    return [
        ("코스피", 4840.74, 43.19),
        ("코스닥", 954.59, 3.43),
        ("나스닥", 23515.38, -14.63),
        ("다우", 49359.33, -83.11),
        ("S&P500", 6940.01, -4.46),
    ]

# =========================
# 3. 주요 원자재
# =========================
def get_commodities():
    return [
        ("금", 2035.40, 12.30),
        ("은", 23.45, -0.12),
        ("WTI", 78.34, 1.02),
        ("가스", 2.41, -0.08),
        ("구리", 3.84, 0.04),
    ]

# =========================
# 4. 주요 암호화폐 (빗썸 기준 예시)
# =========================
def get_crypto():
    return [
        ("BTC", 72450, 1120),
        ("ETH", 3920, 65),
        ("XRP", 615, -12),
        ("SOL", 158, 4),
        ("DOGE", 108, -3),
    ]

# =========================
# basicCard 생성
# =========================
def make_card(title, items):
    desc = "\n".join(
        f"{n} {fmt(p)} {arrow(c)}{fmt(abs(c))}"
        for n, p, c in items
    )

    return {
        "basicCard": {
            "title": title,
            "description": desc
        }
    }

# =========================
# 카카오 스킬 엔드포인트
# =========================
@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    cards = [
        make_card("주요 환율", get_fx()),
        make_card("주요 증시", get_indices()),
        make_card("주요 원자재", get_commodities()),
        make_card("주요 암호화폐", get_crypto()),
    ]

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

# =========================
# 헬스체크
# =========================
@app.route("/health", methods=["GET"])
def health():
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
