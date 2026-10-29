from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
import threading
import time
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

INDEX_CONFIGS = {
    "NASDAQ": {
        "name": "NASDAQ 100",
        "symbol": "^NDX",
        "currency": "$",
        "ladder_step_pct": 0.15,
        "constituents": [
            {"symbol": "NVDA", "name": "Nvidia Corp", "weight": 9.40},
            {"symbol": "AAPL", "name": "Apple Inc", "weight": 8.75},
            {"symbol": "MSFT", "name": "Microsoft Corp", "weight": 7.95},
            {"symbol": "AMZN", "name": "Amazon.com Inc", "weight": 5.45},
            {"symbol": "META", "name": "Meta Platforms", "weight": 4.95},
            {"symbol": "AVGO", "name": "Broadcom Inc", "weight": 4.60},
            {"symbol": "GOOGL", "name": "Alphabet Inc A", "weight": 3.10},
            {"symbol": "GOOG", "name": "Alphabet Inc C", "weight": 2.90},
            {"symbol": "TSLA", "name": "Tesla Inc", "weight": 2.85},
            {"symbol": "COST", "name": "Costco Wholesale", "weight": 2.30},
            {"symbol": "AMD", "name": "Advanced Micro Devices", "weight": 1.95},
            {"symbol": "NFLX", "name": "Netflix Inc", "weight": 1.85},
            {"symbol": "ADBE", "name": "Adobe Inc", "weight": 1.45},
            {"symbol": "QCOM", "name": "Qualcomm Inc", "weight": 1.40},
            {"symbol": "INTC", "name": "Intel Corp", "weight": 1.15},
        ]
    },
    "SP500": {
        "name": "S&P 500",
        "symbol": "^GSPC",
        "currency": "$",
        "ladder_step_pct": 0.12,
        "constituents": [
            {"symbol": "MSFT", "name": "Microsoft Corp", "weight": 7.10},
            {"symbol": "AAPL", "name": "Apple Inc", "weight": 6.90},
            {"symbol": "NVDA", "name": "Nvidia Corp", "weight": 6.75},
            {"symbol": "AMZN", "name": "Amazon.com Inc", "weight": 3.80},
            {"symbol": "META", "name": "Meta Platforms", "weight": 2.65},
            {"symbol": "GOOGL", "name": "Alphabet Inc A", "weight": 2.20},
            {"symbol": "BRK-B", "name": "Berkshire Hathaway", "weight": 1.85},
            {"symbol": "AVGO", "name": "Broadcom Inc", "weight": 1.80},
            {"symbol": "LLY", "name": "Eli Lilly", "weight": 1.65},
            {"symbol": "JPM", "name": "JPMorgan Chase", "weight": 1.50},
            {"symbol": "TSLA", "name": "Tesla Inc", "weight": 1.45},
            {"symbol": "UNH", "name": "UnitedHealth Group", "weight": 1.30},
            {"symbol": "XOM", "name": "Exxon Mobil", "weight": 1.15},
            {"symbol": "V", "name": "Visa Inc", "weight": 1.05},
        ]
    },
    "DOW": {
        "name": "Dow Jones 30",
        "symbol": "^DJI",
        "currency": "$",
        "ladder_step_pct": 0.10,
        "constituents": [
            {"symbol": "UNH", "name": "UnitedHealth Group", "weight": 8.60},
            {"symbol": "GS", "name": "Goldman Sachs", "weight": 8.10},
            {"symbol": "MSFT", "name": "Microsoft Corp", "weight": 6.70},
            {"symbol": "HD", "name": "Home Depot", "weight": 6.20},
            {"symbol": "CAT", "name": "Caterpillar Inc", "weight": 5.80},
            {"symbol": "AMGN", "name": "Amgen Inc", "weight": 4.90},
            {"symbol": "MCD", "name": "McDonald's Corp", "weight": 4.50},
            {"symbol": "V", "name": "Visa Inc", "weight": 4.40},
            {"symbol": "CRM", "name": "Salesforce Inc", "weight": 4.10},
            {"symbol": "AAPL", "name": "Apple Inc", "weight": 3.70},
            {"symbol": "BA", "name": "Boeing Co", "weight": 3.10},
            {"symbol": "JNJ", "name": "Johnson & Johnson", "weight": 2.60},
            {"symbol": "JPM", "name": "JPMorgan Chase", "weight": 2.50},
        ]
    },
    "FTSE": {
        "name": "FTSE 100 (UK)",
        "symbol": "^FTSE",
        "currency": "£",
        "ladder_step_pct": 0.12,
        "constituents": [
            {"symbol": "AZN.L", "name": "AstraZeneca PLC", "weight": 8.90},
            {"symbol": "SHEL.L", "name": "Shell PLC", "weight": 8.40},
            {"symbol": "HSBA.L", "name": "HSBC Holdings", "weight": 6.10},
            {"symbol": "ULVR.L", "name": "Unilever PLC", "weight": 5.20},
            {"symbol": "BP.L", "name": "BP PLC", "weight": 3.90},
            {"symbol": "GSK.L", "name": "GSK PLC", "weight": 3.20},
            {"symbol": "REL.L", "name": "RELX PLC", "weight": 3.10},
            {"symbol": "RIO.L", "name": "Rio Tinto", "weight": 2.90},
            {"symbol": "DGE.L", "name": "Diageo PLC", "weight": 2.80},
            {"symbol": "BATS.L", "name": "British American Tobacco", "weight": 2.60},
            {"symbol": "GLEN.L", "name": "Glencore PLC", "weight": 2.40},
            {"symbol": "LSEG.L", "name": "London Stock Exchange Group", "weight": 2.10},
        ]
    }
}

CACHE = {}
CACHE_LOCK = threading.Lock()
CACHE_TTL = 15

def fetch_chart(symbol):
    with CACHE_LOCK:
        if symbol in CACHE:
            entry = CACHE[symbol]
            if time.time() - entry["ts"] < CACHE_TTL:
                return entry["data"]

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval=1d&range=5d"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3.5) as response:
            data = json.loads(response.read().decode('utf-8'))
            res = data['chart']['result'][0]
            with CACHE_LOCK:
                CACHE[symbol] = {"ts": time.time(), "data": res}
            return res
    except Exception:
        with CACHE_LOCK:
            if symbol in CACHE:
                return CACHE[symbol]["data"]
        return None

def analyze_index(index_key):
    cfg = INDEX_CONFIGS.get(index_key, INDEX_CONFIGS["NASDAQ"])
    
    idx_raw = fetch_chart(cfg["symbol"])
    idx_meta = idx_raw.get('meta', {}) if idx_raw else {}

    current_idx_price = idx_meta.get('regularMarketPrice') or idx_meta.get('previousClose') or 29400.0
    prev_close = idx_meta.get('chartPreviousClose') or idx_meta.get('previousClose') or current_idx_price
    idx_day_high = idx_meta.get('regularMarketDayHigh', current_idx_price * 1.004)
    idx_day_low = idx_meta.get('regularMarketDayLow', current_idx_price * 0.996)
    idx_52_high = idx_meta.get('fiftyTwoWeekHigh', current_idx_price * 1.15)
    idx_52_low = idx_meta.get('fiftyTwoWeekLow', current_idx_price * 0.75)
    idx_chg_pts = current_idx_price - prev_close
    idx_chg_pct = (idx_chg_pts / prev_close) * 100 if prev_close else 0.0

    symbols = [c["symbol"] for c in cfg["constituents"]]
    raw_dict = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_chart, sym): sym for sym in symbols}
        for future in futures:
            sym = futures[future]
            try:
                raw_dict[sym] = future.result()
            except Exception:
                raw_dict[sym] = None

    constituent_results = []
    total_net_points_attributed = 0.0
    bullish_weight = 0.0
    bearish_weight = 0.0
    neutral_weight = 0.0

    for c in cfg["constituents"]:
        sym = c["symbol"]
        weight = c["weight"]
        raw = raw_dict.get(sym)
        if raw and 'meta' in raw:
            meta = raw['meta']
            curr_price = meta.get('regularMarketPrice', 0.0)
            stock_prev_close = meta.get('chartPreviousClose') or meta.get('previousClose') or curr_price
            stock_day_high = meta.get('regularMarketDayHigh', curr_price)
            stock_day_low = meta.get('regularMarketDayLow', curr_price)
            stock_52_high = meta.get('fiftyTwoWeekHigh', curr_price * 1.15)
            stock_52_low = meta.get('fiftyTwoWeekLow', curr_price * 0.8)
        else:
            curr_price = 150.0
            stock_prev_close = 149.0
            stock_day_high = 152.0
            stock_day_low = 148.5
            stock_52_high = 180.0
            stock_52_low = 110.0

        pct_change = ((curr_price - stock_prev_close) / stock_prev_close * 100) if stock_prev_close else 0.0
        
        point_impact = (weight / 100.0) * (pct_change / 100.0) * current_idx_price
        total_net_points_attributed += point_impact

        prev_range_span = (stock_day_high - stock_day_low) if stock_day_high > stock_day_low else (curr_price * 0.01)
        range_pos = max(0.0, min(1.0, (curr_price - stock_day_low) / prev_range_span)) if prev_range_span > 0 else 0.5
        
        span_52 = (stock_52_high - stock_52_low) if stock_52_high > stock_52_low else (curr_price * 0.1)
        pos_52 = max(0.0, min(1.0, (curr_price - stock_52_low) / span_52)) if span_52 > 0 else 0.5

        if pct_change >= 0.3:
            stance = "Strong Bullish"
            signal = "BUY ON DIP / RIDE"
            bullish_weight += weight
        elif pct_change > 0.0:
            stance = "Mild Bullish"
            signal = "MOMENTUM ACCUMULATION"
            bullish_weight += weight
        elif pct_change <= -0.3:
            stance = "Bearish Pressure"
            signal = "SELL / RESISTANCE REJECT"
            bearish_weight += weight
        else:
            stance = "Neutral / Base"
            signal = "RANGE BOUND"
            neutral_weight += weight

        constituent_results.append({
            "symbol": sym,
            "name": c["name"],
            "weight": round(weight, 2),
            "price": round(curr_price, 2),
            "prev_close": round(stock_prev_close, 2),
            "pct_change": round(pct_change, 2),
            "day_high": round(stock_day_high, 2),
            "day_low": round(stock_day_low, 2),
            "fiftyTwo_high": round(stock_52_high, 2),
            "fiftyTwo_low": round(stock_52_low, 2),
            "point_impact": round(point_impact, 2),
            "range_pos": round(range_pos * 100, 1),
            "pos_52": round(pos_52 * 100, 1),
            "stance": stance,
            "signal": signal
        })

    constituent_results.sort(key=lambda x: abs(x["point_impact"]), reverse=True)

    base_step = round(current_idx_price * 0.0015, 0)
    if base_step == 0:
        base_step = 25.0
    
    ladder_levels = []
    for offset in [-4, -3, -2, -1, 0, 1, 2, 3, 4]:
        lvl_price = round(current_idx_price + (offset * base_step), 1)
        pct_diff = round(((lvl_price - current_idx_price) / current_idx_price) * 100, 2)
        
        if offset == 0:
            status = "CURRENT PIVOT"
            conf = "Active Price"
            certainty = 100
        elif offset > 0:
            status = f"RESISTANCE TARGET +{offset}"
            certainty = min(95, max(15, int(45 + (bullish_weight - bearish_weight) * 0.8 - (offset * 8))))
            conf = f"Needs {constituent_results[0]['symbol']} & {constituent_results[1]['symbol']} to hold > intraday VWAP + volume surge"
        else:
            status = f"SUPPORT / DIP BUY {abs(offset)}"
            certainty = min(95, max(15, int(50 + (bearish_weight - bullish_weight) * 0.5 - (abs(offset) * 6))))
            conf = f"Key rebound zone if {constituent_results[0]['symbol']} tests Day Low with absorption"

        ladder_levels.append({
            "level": lvl_price,
            "offset_pct": pct_diff,
            "role": status,
            "probability": f"{certainty}%",
            "condition": conf
        })

    market_bias = "BULLISH ACCUMULATION" if (bullish_weight > bearish_weight + 10) else ("BEARISH CONSOLIDATION" if bearish_weight > bullish_weight + 10 else "NEUTRAL / BALANCED CHOP")
    prob_move = min(92, max(25, int(50 + abs(bullish_weight - bearish_weight) * 0.8)))
    expected_direction = "UPWARD (+0.2% to +0.5%)" if bullish_weight > bearish_weight else "DOWNWARD / DIP TEST (-0.2% to -0.5%)"

    return {
        "index_name": cfg["name"],
        "index_symbol": cfg["symbol"],
        "currency": cfg["currency"],
        "price": round(current_idx_price, 2),
        "prev_close": round(prev_close, 2),
        "change_pts": round(idx_chg_pts, 2),
        "change_pct": round(idx_chg_pct, 2),
        "day_high": round(idx_day_high, 2),
        "day_low": round(idx_day_low, 2),
        "fiftyTwo_high": round(idx_52_high, 2),
        "fiftyTwo_low": round(idx_52_low, 2),
        "bias": market_bias,
        "direction": expected_direction,
        "certainty": f"{prob_move}%",
        "net_point_impact": round(total_net_points_attributed, 2),
        "bullish_weight_pct": round(bullish_weight, 1),
        "bearish_weight_pct": round(bearish_weight, 1),
        "neutral_weight_pct": round(neutral_weight, 1),
        "ladder": ladder_levels,
        "constituents": constituent_results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        idx = query.get("index", ["NASDAQ"])[0]
        try:
            data = analyze_index(idx)
            payload = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as e:
            err = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(err)
