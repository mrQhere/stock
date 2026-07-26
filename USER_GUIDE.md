# Stock Market Predictor: User Guide

Welcome to the **Stock Market Predictor**, an autonomous quantitative analysis engine that tracks assets, trains AI models, and runs Monte Carlo simulations completely locally. 

This guide will walk you through how to use the system.

## 1. Startup Run for First-Time Users

If this is your first time using the platform, the quickest way to see the engine in action is to simply start it with the default configuration.

1. Open your terminal.
2. Run the boot script:
   ```bash
   ./stock_market_boot.sh
   ```
3. The system will automatically download data for a default set of assets, train the initial AI models, and launch the web dashboard.
4. Wait for the URL to appear (usually `http://localhost:8501`) and open it in your browser using the default password `stark`.

## 2. Customizing Your Assets

Before running the system for your own portfolio, you must define which assets you want to track in the `assets.json` file.

Open `assets.json` and add your Yahoo Finance tickers organized by category. For example:
```json
{
  "Tech Stocks": ["AAPL", "MSFT", "GOOGL"],
  "Indices": ["^NSEI", "^GSPC"]
}
```
*Note: Make sure to use the exact ticker symbol as it appears on Yahoo Finance (e.g., `^NSEI` for Nifty 50).*

## 3. Booting the System

To start the system, simply run the boot script from your terminal:
```bash
./stock_market_boot.sh
```

**What happens next?**
1. The script will automatically launch the **Backend Shadow Engine** in a hidden `tmux` session. This engine fetches 5 years of historical data for your assets and trains the XGBoost AI models. It runs continuously in the background, waking up every hour.
2. The script will then launch the **Vision Deployment** (the web dashboard) in another hidden `tmux` session and attach your terminal to it.

## 4. Accessing the Dashboard

When the script finishes booting, it will provide a Local URL (e.g., `http://localhost:8501`). Open this URL in your web browser.

### Security Lock
To ensure your financial data is secure, the web dashboard is locked natively. When you open the page, you must enter the authorization code:
**Password:** `stark`

### How to Change the Password
To change the default password, open `stock_market_ui.py` in your code editor. Locate the password check around line 19:
```python
        if pwd == "stark":
```
Change `"stark"` to your desired password. Save the file and restart the system for the changes to take effect.

## 5. Understanding the Dashboard

Once unlocked, you will see a variety of advanced financial metrics:

- **Long-Term Investing Metrics:** Provides essential capital allocation metrics including 5Y CAGR, Sortino Ratio, Historical Value at Risk (VaR), and Distance from 52-Week Highs/Lows.
- **Advanced Technical Indicators:** Shows the real-time AI inputs for Bollinger Bands, Average True Range (ATR), Stochastic Oscillator, MACD, and RSI.
- **7-Day Forecast Chart:** Shows the actual historical price line alongside the AI's projected 7-day future path.
- **SHAP Logic:** A bar chart showing exactly *why* the AI made its decision (e.g., how much weight it put on Bollinger Bands vs. Volatility).
- **Reality Check (Backtest):** Compares how the AI's strategy would have performed over the last 180 days versus just buying and holding the asset.
- **Monte Carlo Simulation:** A 1,000-path probabilistic simulation of where the price could go over the next year, complete with Black Swan macro stress tests you can toggle on the sidebar (e.g., simulating a 2008 crash).

## 6. Shutting Down

Since the system runs in background `tmux` sessions, simply closing your terminal will *not* stop it. To completely shut down the system, run these commands in your terminal:
```bash
tmux kill-session -t stock_market_backend
tmux kill-session -t stock_market_ui
```

## 7. Troubleshooting

If you encounter issues while running the system, here are some common problems and copy-paste solutions:

**Issue: Port 8501 is already in use**
If you get an error that Streamlit cannot bind to port 8501, it means an old dashboard session is still running.
*Solution:*
```bash
kill -9 $(lsof -t -i:8501)
```

**Issue: tmux sessions won't start or are stuck**
If the boot script hangs or the background jobs fail to start correctly, you may have stale tmux sessions.
*Solution:*
```bash
tmux kill-session -t stock_market_backend
tmux kill-session -t stock_market_ui
```

**Issue: Python dependencies missing**
If you see `ModuleNotFoundError` during boot, your environment may not be set up correctly.
*Solution:*
```bash
source jarvis_env/bin/activate
pip install -r requirements.txt
```
