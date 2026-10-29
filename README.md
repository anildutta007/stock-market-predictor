# ⚡ Global Index Precision Predictor & Attribution Engine

A real-time stock market index forecast and constituent attribution engine for key **US (NASDAQ 100, S&P 500, Dow 30)** and **UK (FTSE 100)** indices.

Built to identify high-certainty index point moves (**0.1% to 0.5% swings**) by measuring constituent weightings, volume-weighted momentum, and level progression ladders.

---

## 🚀 Features

- **Constituent Point Attribution Formula**:
  $$\Delta \text{Index Points}_i = \left(\frac{w_i}{100}\right) \times \left(\frac{\Delta P_i}{P_{i,\text{prev}}}\right) \times I_{\text{base}}$$
  Calculates exact points added or subtracted per constituent stock in real-time.
- **Support & Resistance Ladder (0.1% - 0.5% Progression)**:
  Tracks key price level progressions (e.g. `29425 -> 29455 -> 29500 -> 29560 -> 29600`) with win probabilities and trigger conditions.
- **Prev Day & 52-Week Range Positioning**:
  Gauges intraday range location (0–100%) and 52-week position to flag dips and breakout exhaustions.
- **Weight Heat Distribution**:
  Live breakdown of bullish vs. bearish constituent weight to determine net institutional flow.
- **Multi-Index Coverage**:
  - **NASDAQ 100** (`^NDX`)
  - **S&P 500** (`^GSPC`)
  - **Dow Jones 30** (`^DJI`)
  - **FTSE 100 (UK)** (`^FTSE`)
- **Interactive Dark GUI**:
  Auto-refreshing dashboard with instant tab switching and KPI alerts.

---

## 🛠️ Quick Start

### 1. Requirements
- Python 3.10+ (Standard library only; no external package dependencies required)

### 2. Launch the Application
Double-click `run_stock_market.bat` or run:
```bash
python server.py
```

Open your browser at:
```
http://localhost:8085
```

---

## 📈 Trigger Conditions for 0.1% - 0.5% Moves
1. **Top 3 Mega-Cap Alignment**: When NVDA, AAPL, and MSFT trade synchronously above intraday VWAP with volume expansion, index probability sweeps to the next target level (+0.15% to +0.30%).
2. **Dip Level Buy Trigger**: When price tests the previous day's low or key pivot support with constituent net point delta flipping positive, mark as high-certainty rebound.
