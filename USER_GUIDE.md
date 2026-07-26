# Stock Market Predictor: User Guide

Welcome to the **Stock Market Predictor**, an autonomous quantitative analysis engine that tracks assets, trains AI models, and runs Monte Carlo simulations completely locally. 

This guide will walk you through how to use the system.

## 1. Initial Setup

Before starting the system, you must define which assets you want to track in the `assets.json` file.

Open `assets.json` and add your Yahoo Finance tickers organized by category. For example:
```json
{
  "Tech Stocks": ["AAPL", "MSFT", "GOOGL"],
  "Indices": ["^NSEI", "^GSPC"]
}
```
*Note: Make sure to use the exact ticker symbol as it appears on Yahoo Finance (e.g., `^NSEI` for Nifty 50).*

## 2. Booting the System

To start the system, simply run the boot script from your terminal:
```bash
./stock_market_boot.sh
```

**What happens next?**
1. The script will automatically launch the **Backend Shadow Engine** in a hidden `tmux` session. This engine fetches 5 years of historical data for your assets and trains the XGBoost AI models. It runs continuously in the background, waking up every hour.
2. The script will then launch the **Vision Deployment** (the web dashboard) in another hidden `tmux` session and attach your terminal to it.

## 3. Accessing the Dashboard

When the script finishes booting, it will provide a Local URL (e.g., `http://localhost:8501`). Open this URL in your web browser.

### Security Lock
To ensure your financial data is secure, the web dashboard is locked natively. When you open the page, you must enter the authorization code:
**Password:** `stark`

## 4. Understanding the Dashboard

Once unlocked, you will see a variety of advanced financial metrics:

- **AI Tactical Verdict:** An algorithmic summary of the AI's confidence, expected direction, and current market volatility.
- **7-Day Forecast Chart:** Shows the actual historical price line alongside the AI's projected 7-day future path.
- **SHAP Logic:** A bar chart showing exactly *why* the AI made its decision (e.g., how much weight it put on Moving Averages vs. Volatility).
- **Reality Check (Backtest):** Compares how the AI's strategy would have performed over the last 180 days versus just buying and holding the asset.
- **Monte Carlo Simulation:** A 1,000-path probabilistic simulation of where the price could go over the next 30 days, complete with Black Swan macro stress tests you can toggle on the sidebar (e.g., simulating a 2008 crash).

## 5. Shutting Down

Since the system runs in background `tmux` sessions, simply closing your terminal will *not* stop it. To completely shut down the system, run these commands in your terminal:
```bash
tmux kill-session -t stock_market_backend
tmux kill-session -t stock_market_ui
```
