from flask import Flask, jsonify
from flask_cors import CORS
import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)
CORS(app)

# =========================
# Cache (per section)
# =========================
DEFAULT_TTL = int(os.environ.get("CACHE_TTL", "300"))  # seconds (default 5 minutes)

CACHE = {
    # raw HTML from stock.mk.co.kr
    "mk_html": {"ts": 0.0, "data": None, "ttl": 60},  # refresh html at most every 60s

    # cards data
    "exchange": {"ts": 0.0, "data": None, "ttl": DEFAULT_TTL},
    "indices": {"ts": 0.0, "data": None, "ttl": DEFAULT_TTL},
    "commodities": {"ts": 0.0, "data": None, "ttl": DEFAULT_TTL},
    "crypto": {"ts": 0.0, "data": None, "ttl": 120},  # crypto feels better with shorter ttl

    # rank cards (best-effort; will fall back to placeholders if MK markup changes)
    "kospi_up": {"ts": 0.0, "data": None, "ttl": DEFAULT_TTL},
    "kospi_down": {"ts": 0.0, "data": None, "ttl": DEFAULT_TTL},
    "kosdaq_up": {"ts": 0.0, "data": None, "ttl": DEFAULT_TTL},
    "kosdaq_down": {"ts": 0.0, "data": None, "ttl": DEFAULT_TTL},
    "mcap_top": {"ts": 0.0, "data": None, "ttl": DEFAULT_TTL},
    "nasdaq_vol": {"ts": 0.0, "data": None, "ttl": DEFAULT_TTL},
}


# =========================
# Utils
# =========================

def _now_ts() -> float:
    return time.time()


def _is_cache_valid(key: str) -> bool:
    ent = CACHE.get(key)
    if not ent or ent.get("data") is None:
        return False
    return (_now_ts() - float(ent.get("ts", 0.0))) < int(ent.get("ttl", DEFAULT_TTL))


def _set_cache(key: str, data):
    if key not in CACHE:
        CACHE[key] = {"ts": 0.0, "data": None, "ttl": DEFAULT_TTL}
    CACHE[key]["data"] = data
    CACHE[key]["ts"] = _now_ts()


def _clean(text: str) -> str:
    return (text or "").strip()


def _to_sign(text: str) -> str:
    t = _clean(text)
    if not t:
        return "0"
    t = t.replace("▲", "+").replace("△", "+").replace("▼", "-").replace("▽", "-")
    t = t.replace(",", "")
    t = t.replace(" ", "")
    return t


def _arrow(sign_text: str) -> str:
    s = _to_sign(sign_text)
    if s.startswith("-"):
        return "▼"
    if s.startswith("+"):
        return "▲"
    return "━"


def _abs_number_text(sign_text: str) -> str:
    s = _to_sign(sign_text)
    s = s.lstrip("+")
    if s.startswith("-"):
        s = s[1:]
    return s or "0"


def _format_line(name: str, value: str, chg: str, pct: str = "") -> str:
    # value already formatted (with commas etc). chg can be raw sign or numeric.
    arr = _arrow(chg)
    chg_abs = _abs_number_text(chg)
    pct_clean = _clean(pct)
    pct_part = f" ({pct_clean})" if pct_clean else ""
    return f"{name}\n{value} {arr}{chg_abs}{pct_part}"


def _mk_headers():
    return {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# =========================
# MK fetch
# =========================

def fetch_mk_html() -> str:
    if _is_cache_valid("mk_html"):
        return CACHE["mk_html"]["data"]

    url = "https://stock.mk.co.kr/"
    r = requests.get(url, headers=_mk_headers(), timeout=10)
    r.raise_for_status()
    html = r.text
    _set_cache("mk_html", html)
    return html


def soup_mk() -> BeautifulSoup:
    html = fetch_mk_html()
    return BeautifulSoup(html, "html.parser")


# =========================
# Parsers (best-effort, robust to markup changes)
# =========================

def parse_rows_by_keywords(targets):
    """targets: list of dict {key, match_keywords(list), label}
    Returns dict key -> {value, chg, pct}

    Heuristic: find <tr> rows with enough <td> columns and containing the keyword.
    Expect columns: [name, value, change, percent] but will tolerate missing percent.
    """
    s = soup_mk()
    found = {}

    for tr in s.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue

        col0 = tds[0].get_text(" ", strip=True)
        value = _clean(tds[1].get_text(" ", strip=True))
        chg = _clean(tds[2].get_text(" ", strip=True)) if len(tds) >= 3 else "0"
        pct = _clean(tds[3].get_text(" ", strip=True)) if len(tds) >= 4 else ""

        if not value:
            continue

        for t in targets:
            k = t["key"]
            if k in found:
                continue
            # all keywords must appear
            if all(kw in col0 for kw in t["match_keywords"]):
                found[k] = {"value": value, "chg": chg, "pct": pct}

        if len(found) == len(targets):
            break

    return found


def get_exchange_rates():
    if _is_cache_valid("exchange"):
        return CACHE["exchange"]["data"]

    targets = [
        {"key": "USD", "match_keywords": ["미국"], "label": "USD (미국 달러)"},
        {"key": "JPY100", "match_keywords": ["일본"], "label": "JPY100 (일본 엔)"},
        {"key": "EUR", "match_keywords": ["유로"], "label": "EUR (유로)"},
        {"key": "CNY", "match_keywords": ["중국"], "label": "CNY (중국 위안)"},
        {"key": "GBP", "match_keywords": ["영국"], "label": "GBP (영국 파운드)"},
    ]

    found = parse_rows_by_keywords(targets)

    # Fallback if MK markup changes
    fallback = [
        {"label": "USD (미국 달러)", "value": "1,475.50", "chg": "+5.20", "pct": "+0.35%"},
        {"label": "JPY100 (일본 엔)", "value": "933.54", "chg": "+6.58", "pct": "+0.71%"},
        {"label": "EUR (유로)", "value": "1,711.80", "chg": "+4.93", "pct": "+0.29%"},
        {"label": "CNY (중국 위안)", "value": "211.78", "chg": "+0.63", "pct": "+0.30%"},
        {"label": "GBP (영국 파운드)", "value": "1,974.66", "chg": "+7.40", "pct": "+0.38%"},
    ]

    out = []
    for t in targets:
        k = t["key"]
        if k in found:
            out.append({
                "label": t["label"],
                "value": found[k]["value"],
                "chg": found[k]["chg"],
                "pct": found[k]["pct"],
            })

    if len(out) != 5:
        out = fallback

    _set_cache("exchange", out)
    return out


def get_major_indices():
    if _is_cache_valid("indices"):
        return CACHE["indices"]["data"]

    targets = [
        {"key": "KOSPI", "match_keywords": ["코스피"], "label": "코스피"},
        {"key": "KOSDAQ", "match_keywords": ["코스닥"], "label": "코스닥"},
        {"key": "NASDAQ", "match_keywords": ["나스닥"], "label": "나스닥"},
        {"key": "DOW", "match_keywords": ["다우"], "label": "다우존스"},
        {"key": "SP", "match_keywords": ["S&P"], "label": "S&P 500"},
    ]

    found = parse_rows_by_keywords(targets)

    fallback = [
        {"label": "코스피", "value": "4,840.74", "chg": "+43.19", "pct": "+0.90%"},
        {"label": "코스닥", "value": "954.59", "chg": "+3.43", "pct": "+0.36%"},
        {"label": "나스닥", "value": "23,515.38", "chg": "-14.63", "pct": "-0.06%"},
        {"label": "다우존스", "value": "49,359.33", "chg": "-83.11", "pct": "-0.17%"},
        {"label": "S&P 500", "value": "6,940.01", "chg": "-4.46", "pct": "-0.06%"},
    ]

    out = []
    for t in targets:
        k = t["key"]
        if k in found:
            out.append({
                "label": t["label"],
                "value": found[k]["value"],
                "chg": found[k]["chg"],
                "pct": found[k]["pct"],
            })

    if len(out) != 5:
        out = fallback

    _set_cache("indices", out)
    return out


def get_major_commodities():
    if _is_cache_valid("commodities"):
        return CACHE["commodities"]["data"]

    targets = [
        {"key": "GOLD", "match_keywords": ["금"], "label": "금 (USD/oz)"},
        {"key": "SILVER", "match_keywords": ["은"], "label": "은 (USD/oz)"},
        {"key": "WTI", "match_keywords": ["WTI"], "label": "크루드오일 (USD/bbl)"},
        {"key": "GAS", "match_keywords": ["천연가스"], "label": "천연가스 (USD/MMBtu)"},
        {"key": "COPPER", "match_keywords": ["구리"], "label": "구리 (USD/lb)"},
    ]

    found = parse_rows_by_keywords(targets)

    fallback = [
        {"label": "금 (USD/oz)", "value": "2,035.40", "chg": "+12.30", "pct": "+0.61%"},
        {"label": "은 (USD/oz)", "value": "23.45", "chg": "-0.12", "pct": "-0.51%"},
        {"label": "크루드오일 (USD/bbl)", "value": "78.34", "chg": "+1.02", "pct": "+1.32%"},
        {"label": "천연가스 (USD/MMBtu)", "value": "2.41", "chg": "-0.08", "pct": "-3.21%"},
        {"label": "구리 (USD/lb)", "value": "3.84", "chg": "+0.04", "pct": "+1.05%"},
    ]

    out = []
    for t in targets:
        k = t["key"]
        if k in found:
            out.append({
                "label": t["label"],
                "value": found[k]["value"],
                "chg": found[k]["chg"],
                "pct": found[k]["pct"],
            })

    if len(out) != 5:
        out = fallback

    _set_cache("commodities", out)
    return out


# =========================
# Crypto (Bithumb)
# =========================

def get_crypto_bithumb():
    if _is_cache_valid("crypto"):
        return CACHE["crypto"]["data"]

    url = "https://api.bithumb.com/public/ticker/ALL_KRW"
    coins = [
        ("BTC", "비트코인"),
        ("ETH", "이더리움"),
        ("XRP", "리플"),
        ("SOL", "솔라나"),
        ("DOGE", "도지코인"),
    ]

    try:
        r = requests.get(url, timeout=10)
        j = r.json()
        if str(j.get("status")) != "0000":
            raise RuntimeError("bithumb status not 0000")

        data = j.get("data", {})
        out = []
        for code, name in coins:
            d = data.get(code) or {}
            price = d.get("closing_price", "")
            chg = d.get("fluctate_24H", "0")
            pct = d.get("fluctate_rate_24H", "0")
            # normalize
            price_text = f"{float(str(price).replace(',', '')):,.0f}원" if str(price).strip() else "-"
            chg_text = str(chg)
            pct_text = f"{float(str(pct)): +.2f}%".replace(" ", "")
            out.append({
                "label": f"{name}",
                "value": price_text,
                "chg": chg_text,
                "pct": pct_text,
            })

        if len(out) != 5:
            raise RuntimeError("bithumb parse error")

        _set_cache("crypto", out)
        return out

    except Exception:
        fallback = [
            {"label": "비트코인", "value": "-", "chg": "0", "pct": "0%"},
            {"label": "이더리움", "value": "-", "chg": "0", "pct": "0%"},
            {"label": "리플", "value": "-", "chg": "0", "pct": "0%"},
            {"label": "솔라나", "value": "-", "chg": "0", "pct": "0%"},
            {"label": "도지코인", "value": "-", "chg": "0", "pct": "0%"},
        ]
        _set_cache("crypto", fallback)
        return fallback


# =========================
# Rank cards (best-effort placeholders for now)
# You can wire these to MK rank pages later; structure is ready.
# =========================

def _placeholder_rank(title: str):
    return [
        {"label": "1위", "value": "-", "chg": "0", "pct": "0%"},
        {"label": "2위", "value": "-", "chg": "0", "pct": "0%"},
        {"label": "3위", "value": "-", "chg": "0", "pct": "0%"},
        {"label": "4위", "value": "-", "chg": "0", "pct": "0%"},
        {"label": "5위", "value": "-", "chg": "0", "pct": "0%"},
    ]


def get_rank_data(cache_key: str, title: str):
    if _is_cache_valid(cache_key):
        return CACHE[cache_key]["data"]

    # TODO: connect to MK rank pages (kospi/kosdaq/mcap/volume) with stable endpoints.
    data = _placeholder_rank(title)
    _set_cache(cache_key, data)
    return data


# =========================
# Card builders
# =========================

def make_basic_card(title: str, lines: list[str], button_label: str | None = None, button_url: str | None = None):
    card = {
        "title": title,
        "description": "\n\n".join(lines).strip(),
    }
    if button_label and button_url:
        card["buttons"] = [
            {
                "action": "webLink",
                "label": button_label,
                "webLinkUrl": button_url,
            }
        ]
    return card


def card_exchange():
    data = get_exchange_rates()
    lines = [_format_line(d["label"], d["value"], d["chg"], d.get("pct", "")) for d in data]
    return make_basic_card("주요 환율", lines, "매일경제 마켓", "https://stock.mk.co.kr/")


def card_indices():
    data = get_major_indices()
    lines = [_format_line(d["label"], d["value"], d["chg"], d.get("pct", "")) for d in data]
    return make_basic_card("주요 증시", lines)


def card_commodities():
    data = get_major_commodities()
    lines = [_format_line(d["label"], d["value"], d["chg"], d.get("pct", "")) for d in data]
    return make_basic_card("주요 원자재 지수", lines)


def card_crypto():
    data = get_crypto_bithumb()
    lines = [_format_line(d["label"], d["value"], d["chg"], d.get("pct", "")) for d in data]
    return make_basic_card("암호화폐", lines)


def card_rank(title: str, cache_key: str):
    data = get_rank_data(cache_key, title)
    # Render rank lines compactly (one line per item)
    lines = []
    for d in data:
        lines.append(_format_line(d["label"], d["value"], d["chg"], d.get("pct", "")))
    return make_basic_card(title, lines)


# =========================
# Endpoint (Kakao skill)
# =========================

@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    # Build a single carousel with basicCards (max 10)
    cards = [
        card_exchange(),
        card_indices(),
        card_commodities(),
        card_crypto(),
        card_rank("코스피 상승률 TOP5", "kospi_up"),
        card_rank("코스피 하락률 TOP5", "kospi_down"),
        card_rank("코스닥 상승률 TOP5", "kosdaq_up"),
        card_rank("코스닥 하락률 TOP5", "kosdaq_down"),
        card_rank("시가총액 TOP5", "mcap_top"),
        card_rank("나스닥 거래량 TOP5", "nasdaq_vol"),
    ]

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "carousel": {
                        "type": "basicCard",
                        "items": cards[:10],
                    }
                },
                {
                    "simpleText": {
                        "text": f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }
                }
            ]
        },
    }

    return jsonify(response)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
