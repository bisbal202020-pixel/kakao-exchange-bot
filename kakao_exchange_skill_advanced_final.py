from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import threading

app = Flask(__name__)

# =========================
# 캐시 설정
# =========================
CACHE_TTL = 600  # 10분
_cached_data = None
_cached_time = None
_cache_lock = threading.Lock()


# =========================
# 헬스 체크
# =========================
@app.route("/health", methods=["GET", "HEAD"])
def health():
    return "ok", 200


# =========================
# 환율 스크래핑
# =========================
def fetch_exchange_rates():
    url = "https://stock.mk.co.kr/"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(url, headers=headers, timeout=5)
    soup = BeautifulSoup(res.text, "html.parser")

    table = soup.select_one("table")
    rows = table.select("tr")[1:]

    rates = []

    for row in rows:
        cols = row.select("td")
        if len(cols) < 4:
            continue

        name = cols[0].get_text(strip=True)
        rate = cols[1].get_text(strip=True)
        change = cols[2].get_text(strip=True)
        percent = cols[3].get_text(strip=True)

        if "미국" in name:
            code = "USD"
            flag = "🇺🇸"
            cname = "미국 달러"
        elif "일본" in name:
            code = "JPY100"
            flag = "🇯🇵"
            cname = "일본 엔"
        elif "유로" in name:
            code = "EUR"
            flag = "🇪🇺"
            cname = "유로"
        elif "중국" in name:
            code = "CNY"
            flag = "🇨🇳"
            cname = "중국 위안"
        elif "영국" in name:
            code = "GBP"
            flag = "🇬🇧"
            cname = "영국 파운드"
        else:
            continue

        rates.append({
            "currency": code,
            "name": cname,
            "rate": rate,
            "change": change,
            "percent": percent,
            "flag": flag
        })

    return rates


# =========================
# fallback 데이터
# =========================
def get_fallback_rates():
    return [
        {"currency": "USD", "name": "미국 달러", "rate": "1,475.50", "change": "+5.20", "percent": "+0.35%", "flag": "🇺🇸"},
        {"currency": "JPY100", "name": "일본 엔", "rate": "933.54", "change": "+6.58", "percent": "+0.71%", "flag": "🇯🇵"},
        {"currency": "EUR", "name": "유로", "rate": "1,711.80", "change": "+4.93", "percent": "+0.29%", "flag": "🇪🇺"},
        {"currency": "CNY", "name": "중국 위안", "rate": "211.78", "change": "+0.63", "percent": "+0.30%", "flag": "🇨🇳"},
        {"currency": "GBP", "name": "영국 파운드", "rate": "1,974.66", "change": "+7.40", "percent": "+0.38%", "flag": "🇬🇧"},
    ]


# =========================
# 포맷 정리 (▲ ▼ + 퍼센트)
# =========================
def format_currency_data(rates):
    formatted = []

    for rate in rates:
        raw = rate.get("change", "0")
        percent = rate.get("percent", "")

        try:
            value = abs(float(raw.replace("+", "").replace("-", "")))
        except:
            value = 0.0

        arrow = "▲" if raw.startswith("+") else "▼" if raw.startswith("-") else "━"

        change_text = f"{arrow}{value}"
        if percent:
            change_text += f" ({percent})"

        formatted.append({
            "currency": f"{rate['flag']} {rate['currency']} ({rate['name']})",
            "rate": rate["rate"],
            "change": change_text
        })

    return formatted


# =========================
# 캐시 포함 환율 조회
# =========================
def get_exchange_data():
    global _cached_data, _cached_time

    with _cache_lock:
        if _cached_data and _cached_time:
            if datetime.now() - _cached_time < timedelta(seconds=CACHE_TTL):
                return _cached_data

        try:
            raw = fetch_exchange_rates()
            if not raw:
                raise Exception("empty")
        except:
            raw = get_fallback_rates()

        formatted = format_currency_data(raw)

        _cached_data = formatted
        _cached_time = datetime.now()

        return formatted


# =========================
# 카카오 스킬 엔드포인트
# =========================
@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    rates = get_exchange_data()

    items = []
    for r in rates:
        items.append({
            "title": r["currency"],
            "description": f"{r['rate']} {r['change']}"
        })

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "listCard": {
                        "header": {
                            "title": "이 시각 환율 (매일경제)"
                        },
                        "items": items,
                        "buttons": [
                            {
                                "label": "매일경제 마켓",
                                "action": "webLink",
                                "webLinkUrl": "https://stock.mk.co.kr/"
                            }
                        ]
                    }
                }
            ]
        }
    })


# =========================
# 실행
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
