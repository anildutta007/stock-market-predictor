"""
Vercel Serverless Function: /api/data.py
Supports:
- /api/data?index=NASDAQ
- /api/history?index=NASDAQ&frequency=daily|weekly|monthly
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
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
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "industry": "Semiconductors & AI Hardware", "market_cap": "$3.45T", "shares_out": 24500000000, "weight": 9.40},
            {"symbol": "AAPL", "name": "Apple Inc.", "industry": "Consumer Electronics", "market_cap": "$3.52T", "shares_out": 15110000000, "weight": 8.75},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "industry": "Enterprise Software & Cloud", "market_cap": "$3.18T", "shares_out": 7430000000, "weight": 7.95},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "industry": "E-Commerce & Cloud Computing", "market_cap": "$2.05T", "shares_out": 10520000000, "weight": 5.45},
            {"symbol": "META", "name": "Meta Platforms Inc.", "industry": "Social Media & AI Services", "market_cap": "$1.52T", "shares_out": 2540000000, "weight": 4.95},
            {"symbol": "AVGO", "name": "Broadcom Inc.", "industry": "Semiconductors & Infrastructure", "market_cap": "$840B", "shares_out": 4680000000, "weight": 4.60},
            {"symbol": "GOOGL", "name": "Alphabet Inc. (Class A)", "industry": "Internet Search & Services", "market_cap": "$2.12T", "shares_out": 5890000000, "weight": 3.10},
            {"symbol": "GOOG", "name": "Alphabet Inc. (Class C)", "industry": "Internet Search & Services", "market_cap": "$2.10T", "shares_out": 5510000000, "weight": 2.90},
            {"symbol": "TSLA", "name": "Tesla Inc.", "industry": "Automotive & Clean Energy", "market_cap": "$820B", "shares_out": 3210000000, "weight": 2.85},
            {"symbol": "COST", "name": "Costco Wholesale Corp.", "industry": "Consumer Staples & Retail", "market_cap": "$395B", "shares_out": 443000000, "weight": 2.30},
            {"symbol": "AMD", "name": "Advanced Micro Devices", "industry": "Semiconductors & Computing", "market_cap": "$260B", "shares_out": 1620000000, "weight": 1.95},
            {"symbol": "NFLX", "name": "Netflix Inc.", "industry": "Entertainment & Streaming", "market_cap": "$310B", "shares_out": 431000000, "weight": 1.85},
            {"symbol": "ADBE", "name": "Adobe Inc.", "industry": "Creative & Cloud Software", "market_cap": "$220B", "shares_out": 442000000, "weight": 1.45},
            {"symbol": "QCOM", "name": "Qualcomm Inc.", "industry": "Wireless & Mobile Chips", "market_cap": "$190B", "shares_out": 1110000000, "weight": 1.40},
            {"symbol": "INTC", "name": "Intel Corp.", "industry": "Semiconductors & Foundries", "market_cap": "$102B", "shares_out": 4320000000, "weight": 1.15},
            {"symbol": "PEP", "name": "PepsiCo Inc.", "industry": "Beverages & Snacks", "market_cap": "$235B", "shares_out": 1370000000, "weight": 1.10},
            {"symbol": "LIN", "name": "Linde PLC", "industry": "Industrial Gases & Chemicals", "market_cap": "$215B", "shares_out": 478000000, "weight": 1.05},
            {"symbol": "TXN", "name": "Texas Instruments", "industry": "Analog Semiconductors", "market_cap": "$185B", "shares_out": 915000000, "weight": 1.00},
            {"symbol": "AMGN", "name": "Amgen Inc.", "industry": "Biopharmaceuticals", "market_cap": "$165B", "shares_out": 535000000, "weight": 0.95},
            {"symbol": "ISRG", "name": "Intuitive Surgical Inc.", "industry": "Robotic Healthcare Devices", "market_cap": "$175B", "shares_out": 355000000, "weight": 0.90}
        ]
    },
    "SP500": {
        "name": "S&P 500",
        "symbol": "^GSPC",
        "currency": "$",
        "ladder_step_pct": 0.12,
        "constituents": [
            {"symbol": "MSFT", "name": "Microsoft Corporation", "industry": "Enterprise Software & Cloud", "market_cap": "$3.18T", "shares_out": 7430000000, "weight": 7.10},
            {"symbol": "AAPL", "name": "Apple Inc.", "industry": "Consumer Electronics", "market_cap": "$3.52T", "shares_out": 15110000000, "weight": 6.90},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "industry": "Semiconductors & AI Hardware", "market_cap": "$3.45T", "shares_out": 24500000000, "weight": 6.75},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "industry": "E-Commerce & Cloud Computing", "market_cap": "$2.05T", "shares_out": 10520000000, "weight": 3.80},
            {"symbol": "META", "name": "Meta Platforms Inc.", "industry": "Social Media & AI Services", "market_cap": "$1.52T", "shares_out": 2540000000, "weight": 2.65},
            {"symbol": "GOOGL", "name": "Alphabet Inc. (Class A)", "industry": "Internet Search & Services", "market_cap": "$2.12T", "shares_out": 5890000000, "weight": 2.20},
            {"symbol": "BRK-B", "name": "Berkshire Hathaway", "industry": "Diversified Financial Holdings", "market_cap": "$990B", "shares_out": 2170000000, "weight": 1.85},
            {"symbol": "AVGO", "name": "Broadcom Inc.", "industry": "Semiconductors & Infrastructure", "market_cap": "$840B", "shares_out": 4680000000, "weight": 1.80},
            {"symbol": "LLY", "name": "Eli Lilly and Company", "industry": "Pharmaceuticals & Biotechnology", "market_cap": "$810B", "shares_out": 950000000, "weight": 1.65},
            {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "industry": "Investment & Retail Banking", "market_cap": "$620B", "shares_out": 2840000000, "weight": 1.50},
            {"symbol": "TSLA", "name": "Tesla Inc.", "industry": "Automotive & Clean Energy", "market_cap": "$820B", "shares_out": 3210000000, "weight": 1.45},
            {"symbol": "UNH", "name": "UnitedHealth Group", "industry": "Managed Healthcare & Insurance", "market_cap": "$540B", "shares_out": 920000000, "weight": 1.30},
            {"symbol": "XOM", "name": "Exxon Mobil Corp.", "industry": "Integrated Oil & Gas", "market_cap": "$480B", "shares_out": 3960000000, "weight": 1.15},
            {"symbol": "V", "name": "Visa Inc.", "industry": "Digital Payment Processing", "market_cap": "$590B", "shares_out": 1980000000, "weight": 1.05},
            {"symbol": "PG", "name": "Procter & Gamble Co.", "industry": "Consumer Staples & Goods", "market_cap": "$395B", "shares_out": 2360000000, "weight": 0.95},
            {"symbol": "JNJ", "name": "Johnson & Johnson", "industry": "Pharmaceuticals & MedTech", "market_cap": "$380B", "shares_out": 2400000000, "weight": 0.90},
            {"symbol": "HD", "name": "The Home Depot Inc.", "industry": "Home Improvement Retail", "market_cap": "$385B", "shares_out": 990000000, "weight": 0.85},
            {"symbol": "MA", "name": "Mastercard Inc.", "industry": "Payment Networks & Services", "market_cap": "$470B", "shares_out": 930000000, "weight": 0.80}
        ]
    },
    "DOW": {
        "name": "Dow Jones 30",
        "symbol": "^DJI",
        "currency": "$",
        "ladder_step_pct": 0.10,
        "constituents": [
            {"symbol": "UNH", "name": "UnitedHealth Group", "industry": "Managed Healthcare & Insurance", "market_cap": "$540B", "shares_out": 920000000, "weight": 8.60},
            {"symbol": "GS", "name": "Goldman Sachs Group", "industry": "Investment Banking & Capital Markets", "market_cap": "$175B", "shares_out": 324000000, "weight": 8.10},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "industry": "Enterprise Software & Cloud", "market_cap": "$3.18T", "shares_out": 7430000000, "weight": 6.70},
            {"symbol": "HD", "name": "The Home Depot Inc.", "industry": "Home Improvement Retail", "market_cap": "$385B", "shares_out": 990000000, "weight": 6.20},
            {"symbol": "CAT", "name": "Caterpillar Inc.", "industry": "Heavy Construction Machinery", "market_cap": "$190B", "shares_out": 485000000, "weight": 5.80},
            {"symbol": "AMGN", "name": "Amgen Inc.", "industry": "Biopharmaceuticals", "market_cap": "$165B", "shares_out": 535000000, "weight": 4.90},
            {"symbol": "MCD", "name": "McDonald's Corporation", "industry": "Restaurants & Fast Food", "market_cap": "$210B", "shares_out": 718000000, "weight": 4.50},
            {"symbol": "V", "name": "Visa Inc.", "industry": "Digital Payment Processing", "market_cap": "$590B", "shares_out": 1980000000, "weight": 4.40},
            {"symbol": "CRM", "name": "Salesforce Inc.", "industry": "Enterprise Cloud CRM Software", "market_cap": "$280B", "shares_out": 965000000, "weight": 4.10},
            {"symbol": "AAPL", "name": "Apple Inc.", "industry": "Consumer Electronics", "market_cap": "$3.52T", "shares_out": 15110000000, "weight": 3.70},
            {"symbol": "BA", "name": "The Boeing Company", "industry": "Aerospace & Defense", "market_cap": "$95B", "shares_out": 615000000, "weight": 3.10},
            {"symbol": "JNJ", "name": "Johnson & Johnson", "industry": "Pharmaceuticals & MedTech", "market_cap": "$380B", "shares_out": 2400000000, "weight": 2.60},
            {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "industry": "Investment & Retail Banking", "market_cap": "$620B", "shares_out": 2840000000, "weight": 2.50},
            {"symbol": "IBM", "name": "International Business Machines", "industry": "IT Infrastructure & Hybrid Cloud", "market_cap": "$195B", "shares_out": 920000000, "weight": 2.40},
            {"symbol": "HON", "name": "Honeywell International", "industry": "Industrial Automation & Aviation", "market_cap": "$135B", "shares_out": 650000000, "weight": 2.30},
            {"symbol": "DIS", "name": "The Walt Disney Company", "industry": "Entertainment & Theme Parks", "market_cap": "$175B", "shares_out": 1810000000, "weight": 2.10}
        ]
    },
    "FTSE": {
        "name": "FTSE 100 (UK)",
        "symbol": "^FTSE",
        "currency": "£",
        "ladder_step_pct": 0.12,
        "constituents": [
            {"symbol": "AZN.L", "name": "AstraZeneca PLC", "industry": "Pharmaceuticals & Oncology", "market_cap": "£185B", "shares_out": 1550000000, "weight": 8.90},
            {"symbol": "SHEL.L", "name": "Shell PLC", "industry": "Integrated Energy & LNG", "market_cap": "£165B", "shares_out": 6250000000, "weight": 8.40},
            {"symbol": "HSBA.L", "name": "HSBC Holdings PLC", "industry": "Global Retail & Commercial Banking", "market_cap": "£130B", "shares_out": 18500000000, "weight": 6.10},
            {"symbol": "ULVR.L", "name": "Unilever PLC", "industry": "Consumer Staples & Personal Care", "market_cap": "£115B", "shares_out": 2490000000, "weight": 5.20},
            {"symbol": "BP.L", "name": "BP PLC", "industry": "Oil, Gas & Renewable Energy", "market_cap": "£68B", "shares_out": 16100000000, "weight": 3.90},
            {"symbol": "GSK.L", "name": "GSK PLC", "industry": "Vaccines & Pharmaceuticals", "market_cap": "£59B", "shares_out": 4120000000, "weight": 3.20},
            {"symbol": "REL.L", "name": "RELX PLC", "industry": "Analytics & Information Systems", "market_cap": "£66B", "shares_out": 1880000000, "weight": 3.10},
            {"symbol": "RIO.L", "name": "Rio Tinto Group", "industry": "Mining & Iron Ore Extraction", "market_cap": "£62B", "shares_out": 1250000000, "weight": 2.90},
            {"symbol": "DGE.L", "name": "Diageo PLC", "industry": "Beverages & Distilleries", "market_cap": "£56B", "shares_out": 2230000000, "weight": 2.80},
            {"symbol": "BATS.L", "name": "British American Tobacco", "industry": "Tobacco & Inhalation Products", "market_cap": "£58B", "shares_out": 2210000000, "weight": 2.60},
            {"symbol": "GLEN.L", "name": "Glencore PLC", "industry": "Natural Resources & Commodity Trading", "market_cap": "£48B", "shares_out": 12200000000, "weight": 2.40},
            {"symbol": "LSEG.L", "name": "London Stock Exchange Group", "industry": "Financial Market Infrastructure", "market_cap": "£52B", "shares_out": 535000000, "weight": 2.10},
            {"symbol": "BARC.L", "name": "Barclays PLC", "industry": "Banking & Financial Services", "market_cap": "£36B", "shares_out": 14900000000, "weight": 1.95},
            {"symbol": "LLOY.L", "name": "Lloyds Banking Group", "industry": "Commercial & Mortgage Banking", "market_cap": "£35B", "shares_out": 62800000000, "weight": 1.85},
            {"symbol": "VOD.L", "name": "Vodafone Group PLC", "industry": "Telecommunications", "market_cap": "£19B", "shares_out": 26800000000, "weight": 1.20}
        ]
    }
}

CACHE = {}
CACHE_LOCK = threading.Lock()
CACHE_TTL = 15

def fetch_chart(symbol, interval="1d", range_param="5d"):
    cache_key = f"{symbol}:{interval}:{range_param}"
    with CACHE_LOCK:
        if cache_key in CACHE:
            entry = CACHE[cache_key]
            if time.time() - entry["ts"] < CACHE_TTL:
                return entry["data"]

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval={interval}&range={range_param}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=4.5) as response:
            data = json.loads(response.read().decode('utf-8'))
            res = data['chart']['result'][0]
            with CACHE_LOCK:
                CACHE[cache_key] = {"ts": time.time(), "data": res}
            return res
    except Exception:
        with CACHE_LOCK:
            if cache_key in CACHE:
                return CACHE[cache_key]["data"]
        return None

def analyze_index(index_key):
    cfg = INDEX_CONFIGS.get(index_key, INDEX_CONFIGS["NASDAQ"])
    
    idx_raw = fetch_chart(cfg["symbol"], interval="1d", range_param="5d")
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
        futures = {executor.submit(fetch_chart, sym, "1d", "5d"): sym for sym in symbols}
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

        one_pct_impact = (weight / 100.0) * 0.01 * current_idx_price

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
            "industry": c.get("industry", "Technology"),
            "market_cap": c.get("market_cap", "$100B"),
            "weight": round(weight, 2),
            "price": round(curr_price, 2),
            "prev_close": round(stock_prev_close, 2),
            "pct_change": round(pct_change, 2),
            "day_high": round(stock_day_high, 2),
            "day_low": round(stock_day_low, 2),
            "fiftyTwo_high": round(stock_52_high, 2),
            "fiftyTwo_low": round(stock_52_low, 2),
            "point_impact": round(point_impact, 2),
            "one_pct_impact": round(one_pct_impact, 2),
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

def fetch_history_3y(symbol, frequency="daily"):
    interval_map = {
        "daily": "1d",
        "weekly": "1wk",
        "monthly": "1mo"
    }
    interval = interval_map.get(frequency, "1d")
    raw = fetch_chart(symbol, interval=interval, range_param="3y")
    if not raw or 'timestamp' not in raw:
        return []

    timestamps = raw.get('timestamp', [])
    indicators = raw.get('indicators', {})
    quotes = indicators.get('quote', [{}])[0]

    opens = quotes.get('open', [])
    highs = quotes.get('high', [])
    lows = quotes.get('low', [])
    closes = quotes.get('close', [])
    volumes = quotes.get('volume', [])

    records = []
    n = len(timestamps)

    for i in range(n):
        c = closes[i] if i < len(closes) else None
        o = opens[i] if i < len(opens) else None
        h = highs[i] if i < len(highs) else None
        l = lows[i] if i < len(lows) else None
        v = volumes[i] if i < len(volumes) else None

        if c is None or o is None or h is None or l is None or v is None:
            continue

        ts = timestamps[i]
        date_str = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
        
        chg_pts = c - o
        chg_pct = (chg_pts / o * 100) if o else 0.0

        hl_range = h - l if h > l else (c * 0.01)
        direction_ratio = (c - o) / hl_range if hl_range > 0 else 0.0
        direction_ratio = max(-0.8, min(0.8, direction_ratio))
        
        buy_pct = 0.50 + (0.45 * direction_ratio)
        buy_pct = max(0.05, min(0.95, buy_pct))
        sell_pct = 1.0 - buy_pct

        buy_vol = int(v * buy_pct)
        sell_vol = int(v * sell_pct)

        records.append({
            "date": date_str,
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": int(v),
            "buy_volume": buy_vol,
            "sell_volume": sell_vol,
            "buy_pct": round(buy_pct * 100, 1),
            "sell_pct": round(sell_pct * 100, 1),
            "chg_pts": round(chg_pts, 2),
            "chg_pct": round(chg_pct, 2)
        })

    records.reverse()
    return records

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        idx = query.get("index", ["NASDAQ"])[0]

        if "/api/history" in parsed.path:
            freq = query.get("frequency", ["daily"])[0]
            cfg = INDEX_CONFIGS.get(idx, INDEX_CONFIGS["NASDAQ"])
            try:
                records = fetch_history_3y(cfg["symbol"], frequency=freq)
                res = {
                    "index_name": cfg["name"],
                    "index_symbol": cfg["symbol"],
                    "currency": cfg["currency"],
                    "frequency": freq,
                    "count": len(records),
                    "readings": records
                }
                payload = json.dumps(res).encode("utf-8")
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
            return

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
