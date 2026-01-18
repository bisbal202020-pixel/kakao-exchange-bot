from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, time, re
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# =====================
# 기본 설정
# =====================
CACHE_TTL = 300
UA = {"User-Agent": "Mozilla/5.0"}

_cache = {"fx": None, "idx": None, "cmd": None, "crypto": None}
_cache_ts = {"fx": 0, "idx": 0, "cmd": 0, "crypto": 0}

# =====================
# Kakao helpers
# =====================
def basic_card(title, desc):
    return {
        "basicCard": {
            "title": title,
            "description": desc
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

def two_line(label, value):
    return f"{label}\n{value}"

# =====================
# 데이터 수집
# =====================
def get_fx():
    if _cache["fx"] and time.time() - _cache_ts["fx"] < CACHE_TTL:
        return _cache["fx"]

    r = requests.get("https://open.er-api.com/v6/latest/USD", headers=UA).json()
    krw = r["rates"]["KRW"]

    data = [
        two_line("🇺🇸 USD", f"{krw:,.2f}"),
        two_line("🇯🇵 JPY100", f"{krw / r['rates']['JPY'] * 100:,.2f}"),
        two_line("🇪🇺 EUR", f"{krw / r['rates']['EUR']:,.2f}"),
        two_line("🇨🇳 CNY", f"{krw / r['rates']['CNY']:,.2f}"),
        two_line("🇬🇧 GBP", f"{krw / r['rates']['GBP']:,.2f}")
    ]

    _cache["fx"] = "\n\n".join(data)
    _cache_ts["fx"] = time.time()
    return _cache["fx"]

def scrape_mk(keywords):
    html = requests.get("https://stock.mk.co.kr/", headers=UA).text
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)

    out = []
    for k, label in keywords:
        m = re.search(rf"{k}.*?(\d[\d,]+\.\d+)", text)
        out.append(two_line(label, m.group(1) if m else "-"))
    return "\n\n".join(out)

def get_indices():
    if _cache["idx"] and time.time() - _cache_ts["idx"] < CACHE_TTL:
        return _cache["idx"]

    data = scrape_mk([
        ("코스피", "🇰🇷 코스피"),
        ("코스닥", "🇰🇷 코스닥"),
        ("나스닥", "🇺🇸 나스닥"),
        ("다우", "🇺🇸 다우"),
        ("S&P", "🇺🇸 S&P500")
    ])

    _cache["idx"] = data
    _cache_ts["idx"] = time.time()
    return data

def get_commodities():
    if _cache["cmd"] and time.time() - _cache_ts["cmd"] < CACHE_TTL:
        return _cache["cmd"]

    data = scrape_mk([
        ("금", "🥇 금"),
        ("은", "🥈 은"),
        ("WTI", "🛢️ WTI"),
        ("가스", "🔥 천연가스"),
        ("구리", "🟠 구리")
    ])

    _cache["cmd"] = data
    _cache_ts["cmd"] = time.time()
    return data

def get_crypto():
    if _cache["crypto"] and time.time() - _cache_ts["crypto"] < CACHE_TTL:
        return _cache["crypto"]

    r = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW").json()["data"]

    coins = [
        two_line("₿ BTC", f"{int(float(r['BTC']['closing_price'])):,}"),
        two_line("⧫ ETH", f"{int(float(r['ETH']['closing_price'])):,}"),
        two_line("✕ XRP", f"{int(float(r['XRP']['closing_price'])):,}"),
        two_line("◎ SOL", f"{int(float(r['SOL']['closing_price'])):,}"),
        two_line("Ð DOGE", f"{float(r['DOGE']['closing_price']):.3f}")
    ]

    _cache["crypto"] = "\n\n".join(coins)
    _cache_ts["crypto"] = time.time()
    return _cache["crypto"]

# =====================
# Routes
# =====================
@app.route("/health")
def health():
    return "OK", 200

@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    cards = [
        basic_card("주요 환율", get_fx()),
        basic_card("주요 증시", get_indices()),
        basic_card("주요 원자재", get_commodities()),
        basic_card("주요 암호화폐", get_crypto())
    ]
    return jsonify(carousel(cards))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
