from flask import Flask, request, jsonify
from flask_cors import CORS

import requests
from bs4 import BeautifulSoup

from datetime import datetime
import time
import re

app = Flask(__name__)
CORS(app)

# ---------------------
# Settings
# ---------------------
CACHE_TTL = 300  # seconds (5 minutes)
REQ_TIMEOUT = 6
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}

# ---------------------
# In-memory cache/state
# ---------------------
_cache = {
    "fx": {"ts": 0.0, "data": None},
    "indices": {"ts": 0.0, "data": None},
    "commod": {"ts": 0.0, "data": None},
    "crypto": {"ts": 0.0, "data": None},
}

_last_value = {
    "fx": {},
    "indices": {},
    "commod": {},
    "crypto": {},
}


# =====================
# Kakao response helpers
# =====================

def basic_card(title: str, description: str):
    # Kakao i OpenBuilder basicCard
    return {
        "basicCard": {
            "title": title,
            "description": description
        }
    }


def carousel_basic(cards):
    return {
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
    }


def _arrow_and_delta(prev: float | None, cur: float):
    """
    Kakao basicCard는 텍스트 컬러 제어 불가.
    => 이모지로 대체: 상승 🔺(빨강), 하락 ▼(파랑)
    """
    if prev is None:
        return "", ""
    delta = cur - prev
    if abs(delta) < 1e-9:
        return "", "0"

    arrow = "🔺" if delta > 0 else "▼"
    # delta는 길이 줄이려고 2자리 고정(필요하면 1자리로 바꿔도 됨)
    return arrow, f"{abs(delta):,.2f}"


def _safe_float(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x)
    s = s.replace(",", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _fmt_two_lines(label: str, value: str, arrow: str = "", delta: str = ""):
    # Keep it short to avoid truncation.
    tail = ""
    if arrow and delta:
        tail = f" {arrow}{delta}"
    return f"{label}\n{value}{tail}"


def _build_description(items):
    # items: list[str]
    # Separate blocks with a blank line.
    return "\n\n".join(items)


# =====================
# Data sources
# =====================

def get_fx():
    """FX: compute KRW quotes from a free rates endpoint; change is vs previous cached value."""
    now = time.time()
    if _cache["fx"]["data"] and (now - _cache["fx"]["ts"]) < CACHE_TTL:
        return _cache["fx"]["data"]

    # 1 USD = rates[currency]
    url = "https://open.er-api.com/v6/latest/USD"
    r = requests.get(url, headers=UA, timeout=REQ_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    rates = j.get("rates", {})

    krw_per_usd = float(rates.get("KRW"))
    eur_per_usd = float(rates.get("EUR"))
    cny_per_usd = float(rates.get("CNY"))
    gbp_per_usd = float(rates.get("GBP"))
    jpy_per_usd = float(rates.get("JPY"))

    def krw_per(code_per_usd: float):
        return krw_per_usd / code_per_usd

    data = [
        {"key": "USD", "label": "🇺🇸 USD", "value": krw_per_usd},
        {"key": "JPY", "label": "🇯🇵 JPY", "value": (krw_per_usd / jpy_per_usd) * 100.0},
        {"key": "EUR", "label": "🇪🇺 EUR", "value": krw_per(eur_per_usd)},
        {"key": "CNY", "label": "🇨🇳 CNY", "value": krw_per(cny_per_usd)},
        {"key": "GBP", "label": "🇬🇧 GBP", "value": krw_per(gbp_per_usd)},
    ]

    # Add change vs last observed
    out = []
    for row in data:
        prev = _last_value["fx"].get(row["key"])  # float | None
        cur = float(row["value"])
        arrow, delta = _arrow_and_delta(prev, cur)
        _last_value["fx"][row["key"]] = cur
        out.append({"label": row["label"], "rate": f"{cur:,.2f}", "arrow": arrow, "delta": delta})

    _cache["fx"] = {"ts": now, "data": out}
    return out


def _mk_html():
    url = "https://stock.mk.co.kr/"
    r = requests.get(url, headers=UA, timeout=REQ_TIMEOUT)
    r.raise_for_status()
    return r.text


def _scrape_value_and_change(text: str, names):
    """Try to scrape 'value' and 'change' near each keyword from MK homepage.
    This is heuristic; if it fails, we still return value-only where possible.
    """
    soup = BeautifulSoup(text, "html.parser")
    plain = soup.get_text(" ", strip=True)

    def find_near(keyword: str):
        idx = plain.find(keyword)
        if idx == -1:
            return None
        window = plain[idx: idx + 180]
        nums = re.findall(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?", window)
        if not nums:
            return None
        value = nums[0]
        change = nums[1] if len(nums) >= 2 else ""
        return value, change

    results = []
    for key, label in names:
        got = find_near(key)
        if got:
            value, change = got
            results.append({"key": key, "label": label, "value": value, "change": change})
        else:
            results.append({"key": key, "label": label, "value": "", "change": ""})
    return results


def get_indices():
    now = time.time()
    if _cache["indices"]["data"] and (now - _cache["indices"]["ts"]) < CACHE_TTL:
        return _cache["indices"]["data"]

    html = _mk_html()
    targets = [
        ("코스피", "🇰🇷 코스피"),
        ("코스닥", "🇰🇷 코스닥"),
        ("나스닥", "🇺🇸 나스닥"),
        ("다우", "🇺🇸 다우"),
        ("S&P", "🇺🇸 S&P500"),
    ]

    scraped = _scrape_value_and_change(html, targets)

    out = []
    for row in scraped:
        v = _safe_float(row["value"])
        if v is not None:
            prev = _last_value["indices"].get(row["key"])  # float | None
            arrow, delta = _arrow_and_delta(prev, v)
            _last_value["indices"][row["key"]] = v
            out.append({"label": row["label"], "value": f"{v:,.2f}", "arrow": arrow, "delta": delta})
        else:
            out.append({"label": row["label"], "value": "-", "arrow": "", "delta": ""})

    _cache["indices"] = {"ts": now, "data": out}
    return out


def get_commodities():
    now = time.time()
    if _cache["commod"]["data"] and (now - _cache["commod"]["ts"]) < CACHE_TTL:
        return _cache["commod"]["data"]

    html = _mk_html()
    targets = [
        ("금", "금(USD/oz)"),
        ("은", "은(USD/oz)"),
        ("WTI", "WTI(USD/bbl)"),
        ("가스", "가스(USD/MMBtu)"),
        ("구리", "구리(USD/lb)"),
    ]

    scraped = _scrape_value_and_change(html, targets)

    out = []
    for row in scraped:
        v = _safe_float(row["value"])
        if v is not None:
            prev = _last_value["commod"].get(row["key"])  # float | None
            arrow, delta = _arrow_and_delta(prev, v)
            _last_value["commod"][row["key"]] = v
            out.append({"label": row["label"], "value": f"{v:,.2f}", "arrow": arrow, "delta": delta})
        else:
            out.append({"label": row["label"], "value": "-", "arrow": "", "delta": ""})

    _cache["commod"] = {"ts": now, "data": out}
    return out


def get_crypto():
    now = time.time()
    if _cache["crypto"]["data"] and (now - _cache["crypto"]["ts"]) < CACHE_TTL:
        return _cache["crypto"]["data"]

    url = "https://api.bithumb.com/public/ticker/ALL_KRW"
    r = requests.get(url, headers=UA, timeout=REQ_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    data = j.get("data", {})

    picks = [
        ("BTC", "비트코인"),
        ("ETH", "이더리움"),
        ("XRP", "리플"),
        ("SOL", "솔라나"),
        ("DOGE", "도지"),
    ]

    out = []
    for sym, label in picks:
        row = data.get(sym, {})
        close = _safe_float(row.get("closing_price"))
        if close is None:
            out.append({"label": label, "value": "-", "arrow": "", "delta": ""})
            continue
        prev = _last_value["crypto"].get(sym)
        arrow, delta = _arrow_and_delta(prev, close)
        _last_value["crypto"][sym] = close
        out.append({"label": label, "value": f"{close:,.0f}원", "arrow": arrow, "delta": delta})

    _cache["crypto"] = {"ts": now, "data": out}
    return out


# =====================
# Routes
# =====================

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


@app.route("/exchange_rate", methods=["POST"])
def exchange_rate():
    _ = request.get_json(silent=True) or {}

    fx = get_fx()
    idxs = get_indices()
    comm = get_commodities()
    crypto = get_crypto()

    fx_desc = _build_description([
        _fmt_two_lines(row["label"], row["rate"], row["arrow"], row["delta"]) for row in fx
    ])
    idx_desc = _build_description([
        _fmt_two_lines(row["label"], row["value"], row["arrow"], row["delta"]) for row in idxs
    ])
    comm_desc = _build_description([
        _fmt_two_lines(row["label"], row["value"], row["arrow"], row["delta"]) for row in comm
    ])
    crypto_desc = _build_description([
        _fmt_two_lines(row["label"], row["value"], row["arrow"], row["delta"]) for row in crypto
    ])

    cards = [
        basic_card("주요 환율", fx_desc),
        basic_card("주요 증시", idx_desc),
        basic_card("주요 원자재", comm_desc),
        basic_card("주요 암호화폐", crypto_desc),
    ]

    return jsonify(carousel_basic(cards))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
