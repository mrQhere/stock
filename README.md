<div align="center">

# 🟢 Indian Stock Market Predictor & ROI Engine

**An autonomous, locally-hosted quantitative analysis engine tailored for the Indian Stock Market (NSE/BSE).**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![XGBoost](https://img.shields.io/badge/AI-XGBoost-orange.svg)](https://xgboost.readthedocs.io/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Designed for absolute privacy and offline capabilities, this system predicts returns on investment (ROI), evaluates risks, and logs the strategic rationale behind its picks.

![Terminal Overview Demo](assets/demo.gif)
*[Watch the full walkthrough on YouTube](https://youtube.com/your-video-link-here)*

</div>

---

## 📑 Table of Contents
- [Core Features](#-core-features)
- [Prerequisites & Setup](#-prerequisites--setup)
- [Architecture & Mechanics](#-architecture--mechanics)
- [Technical Highlights](#-technical-highlights)
- [Tech Stack](#-tech-stack)

---

## ✨ Core Features

- **Long-Term Investing Metrics:** Calculates 5Y CAGR, Sortino Ratio (downside risk), Historical VaR (Value at Risk), and Distance from 52-Week Highs/Lows.
- **Advanced AI Analysis:** XGBoost AI is fed sophisticated technical indicators (Bollinger Bands, ATR, Stochastic Oscillators, MACD, RSI) to gauge momentum and volatility accurately.
- **Explainable AI (SHAP):** Visually breaks down *exactly* which technical indicators drove the AI's buy/sell/hold decision.
- **Monte Carlo Simulations:** 1,000-path probabilistic simulations forecast exact ROI over multiple horizons (7 Days, 1 Month, 1 Year), complete with macro black-swan stress tests.

---

## 🚀 Prerequisites & Setup

To deploy this project on a fresh machine, you will need:
- **Python 3.8+** installed
- **Git** (to clone the repository)
- A **bash-compatible shell** (Linux/macOS)

### Installation

1. **Make the boot script executable:**
   ```bash
   chmod +x stock_market_boot.sh
   ```

2. **Run the ignition sequence:**
   ```bash
   ./stock_market_boot.sh
   ```
   > **Note:** This automatically creates an isolated virtual environment, installs all dependencies, generates default assets, and launches the backend continuously in the background while bringing the frontend to your active terminal.

---

## 🧠 Architecture & Mechanics

### 1. The Shadow Engine (Offline Data Sync)
The backend (`stock_market_backend.py`) operates entirely in the background, minimizing compute and API overhead:
- **Smart Fetching:** Only fetches data when the **Indian Stock Market is open (9:15 AM - 3:30 PM IST, Mon-Fri)**.
- **Local Data Lake:** Downloaded data is securely stored in the `data_lake/` directory as `.csv` and `.json` files.
- **Offline Mode:** The dashboard can be fully viewed offline; it simply loads the latest synced data from the lake.

### 2. The Investing Engine (Metrics & ROI)

The platform runs deep quantitative analysis on the fetched data, generating predictive paths and evaluating the Sharpe/Sortino ratios of the generated portfolios.



### 3. Modifying Background Logic
To customize the update frequency or logic:
1. Open `stock_market_backend.py`.
2. Locate `run_stock_market()` near the bottom of the file.
3. Adjust the `time.sleep(3600)` variable to alter the hourly cycle, or modify `market_open_time` / `market_close_time` for different timezones.

---

## ⚡ Technical Highlights

- **Optimized for Indian Markets:** Pre-configured with major NSE indices and large-cap stocks (e.g., Reliance, TCS, Infosys using `.NS` suffixes).
- **Zero-Telemetry Security:** All data parsing and AI model training happens 100% locally. Zero data is transmitted to third-party APIs beyond the initial Yahoo Finance fetch.
- **Capital Deployment Matrices:** Instantly visualizes the projected value of a ₹10,000 investment under 6 distinct probabilistic scenarios across 7-day, 1-month, and 1-year horizons.

---

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| **Language** | Python 3 |
| **Machine Learning** | XGBoost |
| **Frontend UI** | Streamlit |
| **Data Sourcing** | yfinance |
| **Automation** | Bash Scripting |
| **Timezone Parsing** | pytz |

---

## ⚠️ Disclaimer

This is a personal/educational project and does not constitute financial advice. Past backtest performance is not indicative of future results. Please do not deploy real capital based solely on the outputs of this experimental system.
