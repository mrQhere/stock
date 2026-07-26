# 🟢 Indian Stock Market Predictor & ROI Engine

An autonomous, locally-hosted quantitative analysis engine tailored specifically for the Indian Stock Market (NSE/BSE). Designed for absolute privacy and offline capabilities, this system predicts returns on investment (ROI), evaluates risks, and logs the rationale behind its picks.

## 📋 Prerequisites & Setup

To run this project on a fresh machine, you need:
- **Python 3.8+** installed on your system.
- **Git** (to clone/upload the repository).
- (Linux/Mac) `bash` shell to run the boot script.

To launch the system:
1. Make the boot script executable (if not already): `chmod +x stock_market_boot.sh`
2. Run the ignition sequence: `./stock_market_boot.sh`
   *(This automatically creates a virtual environment, installs dependencies, creates default assets, and launches both backend and frontend).*

## 🧠 Background Working & Mechanics

### 1. Offline Data & Background Sync (The Shadow Engine)
- The backend (`stock_market_backend.py`) runs in the background and only fetches data when the **Indian Stock Market is open (9:15 AM - 3:30 PM IST, Mon-Fri)**.
- If the market is closed, it pauses to save compute and API calls.
- Once downloaded, data is stored in the `data_lake/` folder as `.csv` and `.json` files. 
- You can fully view the dashboard offline; it will load the last synced data from the `data_lake/` folder automatically.

### 2. The Investing Engine (Metrics & ROI)
- **Long-Term Investing Metrics**: Designed for capital allocators, not day-traders. Calculates 5Y CAGR, Sortino Ratio (downside risk), Historical VaR (Value at Risk), Distance from 52-Week highs/lows, and Golden/Death Cross macroeconomic trends.
- **Advanced Technical Inputs**: The XGBoost AI is fed sophisticated technical indicators (Bollinger Bands, Average True Range, Stochastic Oscillators, MACD, RSI) to accurately gauge momentum and volatility.
- **The 'Why' Factor (SHAP)**: The UI visually breaks down which of these indicators drove the AI's buy/sell decision.
- **ROI Projections**: 1,000-path Monte Carlo simulations forecast your exact ROI over multiple horizons (7 Days, 1 Month, 1 Year) based on your invested capital, including macro black-swan scenarios.

### 3. Modifying the Background Logic
If you want to change the background update frequency or logic:
- Open `stock_market_backend.py`.
- Find `run_stock_market()` near the bottom.
- You can adjust the `time.sleep(3600)` to change the hourly cycle, or modify the `market_open_time` / `market_close_time` logic to fit other timezones or custom intervals.

## ⚡ Technical Highlights
* **Optimized for Indian Stocks:** Defaults to major NSE indices and large-cap stocks like Reliance, TCS, and Infosys (`.NS` suffixes).
* **Zero-Telemetry Security:** All data parsing and AI training happens locally. Zero data is sent to third-party APIs beyond the initial Yahoo Finance fetch.
* **Capital Deployment Matrices:** Shows exactly how much a ₹10,000 investment would be worth under 6 different mathematical scenarios across 7 days, 1 month, and 1 year.

## 🛠️ Tech Stack
`Python 3` | `XGBoost` | `Streamlit` | `yfinance` | `Bash Scripting` | `pytz`
