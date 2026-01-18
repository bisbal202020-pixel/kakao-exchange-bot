from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# ===== 10분 캐시 설정 =====
EXCHANGE_CACHE = {"data": None, "timestamp": None}
CACHE_TTL = 600  # seconds

# 우리가 뽑을 대상(표의 '국가/통화명' 텍스트 기준)
TARGET_ROWS = {
    "미국":  {"code": "USD",   "flag": "🇺🇸", "name": "미국 달러"},
    "일본":  {"code": "JPY100","flag": "🇯🇵", "name": "일본 엔"},
    "유로":  {"code": "EUR",   "flag": "🇪🇺", "name": "유로"},
    "중국":  {"code": "CNY",   "flag": "🇨🇳", "name": "중국 위안"},
    "영국":  {"code": "GBP",   "flag": "🇬🇧", "name": "영국 파운드"},
}

def _clean_num(text: str) -> str:
    # "1,974.66" 같은 값만 남기고 양끝 공백 제거
    return (text or "").strip()

def _clean_change(text: str) -> str:
    # "▲ 7.40" / "+7.40" / "7.40" 등 들어와도 +7.40 형태로 맞춤
    t = (text or "").strip()
    t = t.replace("▲", "+").replace("△", "+").replace("▼", "-").replace("▽", "-")
    t = t.replace(" ", "")
    # 이미 +/−가 있으면 유지, 없으면 그냥 그대로(나중에 표시로 처리)
    return t

def get_exchange_rates_advanced():
    now = datetime.now()
    if (
        EXCHANGE_CACHE["data"] is not None
        and EXCHANGE_CACHE["timestamp"] is not None
        and (now - EXCHANGE_CACHE["timestamp"]).seconds < CACHE_TTL
    ):
        return EXCHANGE_CACHE["data"]

    try:
        url = "https://stock.mk.co.kr/"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # 페이지의 모든 tr을 보면서, 첫 td에 "미국/영국/유로/일본/중국"이 있는 행을 잡는다.
        found = {}
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            col0 = tds[0].get_text(" ", strip=True)
            rate = _clean_num(tds[1].get_text(" ", strip=True))
            change = _clean_change(tds[2].get_text(" ", strip=True))

            # TARGET_ROWS 키가 첫 컬럼에 포함되는지로 매칭
            for key, meta in TARGET_ROWS.items():
                if key in col0 and key not in found and rate:
                    found[key] = {
                        "currency": meta["code"],
                        "rate": rate,
                        "change": change if change else "0",
                        "flag": meta["flag"],
                        "name": meta["name"],
                    }

        # 우리가 원하는 5개가 다 안 잡히면 fallback
        rates = [found[k] for k in ["미국", "일본", "유로", "중국", "영국"] if k in found]
        if len(rates) < 5:
            rates = get_fallback_rates()

        EXCHANGE_CACHE["data"] = rates
        EXCHANGE_CACHE["timestamp"] = now
        return rates

    except Exception:
        return get_fallback_rates()

def get_fallback_rates():
    # 네트워크/페이지구조 변경 등으로 스크래핑 실패 시 임시 표시용(값은 예시)
    return [
        {"currency": "USD", "rate": "1,475.50", "change": "+5.20", "flag": "🇺🇸", "name": "미국 달러"},
        {"currency": "JPY100", "rate": "933.54", "change": "+6.58", "flag": "🇯🇵", "name": "일본 엔"},
        {"currency": "EUR", "rate": "1,711.80", "change": "+4.93", "flag": "🇪🇺", "name": "유로"},
        {"currency": "CNY", "rate": "211.78", "change": "+0.63", "flag": "🇨🇳", "name": "중국 위안"},
        {"currency": "GBP", "rate": "1,974.66", "change": "+7.40", "flag": "🇬🇧", "name": "영국 파운드"},
    ]

def format_currency_data(rates):
    formatted = []
    for rate in rates:
        code = (rate.get("currency") or "").split()[0]
        formatted.append({
            "currency": f"{code} ({rate.get('name', code)})",
            "rate": rate.get("rate", ""),
            "change": rate.get("change", "0"),
            "flag": rate.get("flag", "")
        })
    return formatted

@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    rates = format_currency_data(get_exchange_rates_advanced())

    items = []
    for rate in rates[:5]:
        ch = rate["change"] or "0"
        icon = "▲" if ch.startswith("+") else "▼" if ch.startswith("-") else "━"
        value = ch.replace("+", "").replace("-", "")
        items.append({
            "title": f"{rate['flag']} {rate['currency']}",
            "description": f"{rate['rate']}  {icon} {value}"
        })

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "listCard": {
                        "header": {"title": "이 시각 환율 (매일경제)"},
                        "items": items,
                        "buttons": [
                            {
                                "action": "webLink",
                                "label": "매일경제 마켓",
                                "webLinkUrl": "https://stock.mk.co.kr/"
                            }
                        ]
                    }
                },
                {
                    "simpleText": {
                        "text": f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }
                }
            ]
        }
    }
    return jsonify(response)

# ✅ 서버 깨우기 / 헬스체크용
@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
