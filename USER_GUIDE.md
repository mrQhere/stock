# Stock Market Predictor: User Guide

Welcome to the **Stock Market Predictor**, an autonomous quantitative analysis engine that tracks assets, trains AI models, and runs Monte Carlo simulations completely locally. 

This guide provides step-by-step instructions for configuring, running, and understanding the platform.

---

## Table of Contents
1. [Quick Start for First-Time Users](#1-quick-start-for-first-time-users)
2. [Portfolio Customization](#2-portfolio-customization)
3. [System Boot & Architecture](#3-system-boot--architecture)
4. [Security & Access](#4-security--access)
5. [Dashboard Analytics Breakdown](#5-dashboard-analytics-breakdown)
6. [Graceful Shutdown](#6-graceful-shutdown)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Quick Start for First-Time Users

If this is your first time using the platform, the fastest way to evaluate the engine is to run it with the default configuration.

1. Open your terminal.
2. Execute the boot script:
   ```bash
   ./stock_market_boot.sh
   ```
3. The system will automatically download data for a default set of assets, train the initial AI models, and launch the web dashboard.
4. Wait for the local URL to appear (usually `http://localhost:8501`) and open it in your browser.
5. Enter the default authorization password: `stark`.

---

## 2. Portfolio Customization

Before running the system against your own portfolio, you must define the target assets in the configuration file.

Open `assets.json` and add your Yahoo Finance tickers organized by category.

**Example Configuration:**
```json
{
  "Tech Stocks": ["AAPL", "MSFT", "GOOGL"],
  "Indices": ["^NSEI", "^GSPC"]
}
```
> **Note:** Ensure you use the exact ticker symbol as it appears on Yahoo Finance (e.g., `^NSEI` for Nifty 50, `RELIANCE.NS` for Indian Equities).

---

## 3. System Boot & Architecture

To initiate the analysis pipeline, run the boot script from your terminal:
```bash
./stock_market_boot.sh
```

**Boot Sequence Details:**
1. **The Shadow Engine:** The script launches the backend data collector as a persistent background process (`nohup`). This engine fetches 5 years of historical data for your assets and trains the XGBoost AI models. It runs continuously in the background, executing an hourly wake-up cycle.
2. **Vision Deployment:** The script subsequently launches the web dashboard and attaches it directly to your active terminal for monitoring.

---

## 4. Security & Access

Once the boot sequence concludes, navigate to the provided Local URL (e.g., `http://localhost:8501`) in your web browser.

### Authentication Lock
To ensure financial data integrity and privacy, the web dashboard natively requires an authorization code. 

**Default Password:** `stark`

### Password Modification
To change the default password, you must modify the frontend application code.

1. Open `stock_market_ui.py` in your code editor.
2. Locate the password verification logic around line 19:
   ```python
           if pwd == "stark":
   ```
3. Replace `"stark"` with your secure password.
4. Save the file and restart the system to enforce the new credentials.

---

## 5. Dashboard Analytics Breakdown

Upon successful authentication, the dashboard surfaces a comprehensive suite of quantitative metrics:

- **Long-Term Investing Metrics:** Provides essential capital allocation data including 5Y CAGR, Sortino Ratio, Historical Value at Risk (VaR), and Distance from 52-Week Highs/Lows.
- **Advanced Technical Indicators:** Displays real-time AI inputs for Bollinger Bands, Average True Range (ATR), Stochastic Oscillator, MACD, and RSI.
- **7-Day Forecast Chart:** Graphs the actual historical price action against the AI's projected 7-day quantitative path.
- **SHAP Logic (Explainability):** A feature importance chart detailing exactly how much weight the AI assigned to specific indicators when generating its signal.
- **Reality Check (Backtest):** Compares how the AI's algorithmic strategy would have performed over the last 180 days versus a standard buy-and-hold approach.
- **Monte Carlo Simulation:** A 1,000-path probabilistic simulation projecting potential price action over the next year. Includes togglable macroeconomic stress tests (e.g., 2008 Crash, Oil Shock).

---

## 6. Graceful Shutdown

Because the backend runs as a persistent background process, simply closing your terminal window will **not** terminate the data collector.

To completely halt the platform, press `Ctrl+C` in the terminal to stop the UI, then execute the following command to kill the backend:
```bash
pkill -f stock_market_backend.py
```

---

## 7. Troubleshooting

If you encounter operational issues, consult the standard resolutions below.

### Port 8501 Binding Error
**Symptom:** Streamlit throws an error stating port 8501 is already in use.
**Cause:** A previous dashboard session is still running in the background.
**Resolution:**
```bash
kill -9 $(lsof -t -i:8501)
```

### Stale Background Processes
**Symptom:** The boot script hangs, or background jobs fail to execute correctly.
**Cause:** Orphaned or corrupted background processes.
**Resolution:**
```bash
pkill -f stock_market_backend.py
pkill -f stock_market_ui.py
```

### Missing Python Dependencies
**Symptom:** `ModuleNotFoundError` is thrown during the boot sequence.
**Cause:** The virtual environment was not activated, or requirements failed to install.
**Resolution:**
```bash
source jarvis_env/bin/activate
pip install -r requirements.txt
```
