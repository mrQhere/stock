import yfinance as yf
import pandas as pd
import numpy as np
import xgboost as xgb
from arch import arch_model
from sklearn.metrics import r2_score
import json
import os
import time
import warnings
from datetime import datetime
import pytz

warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data_lake")
ASSET_FILE = os.path.join(BASE_DIR, "assets.json")

# Terminal Alert Colors
BLINK_RED = '\033[5;31m'
BOLD_GREEN = '\033[1;32m'
CYAN = '\033[0;36m'
RESET = '\033[0m'

def fetch_and_store_data(ticker, dir_path):
    csv_path = os.path.join(dir_path, "history.csv")
    print(f"\n{CYAN}[{ticker}] Connecting to Data Lake...{RESET}")
    
    try:
        print(f"[{ticker}] Syncing latest 5y market data...")
        data = yf.Ticker(ticker).history(period="5y")
        if data is None or data.empty:
            print(f"[{ticker}] No data returned from yfinance.")
            return None
            
        data.index = data.index.tz_localize(None)
        data.reset_index(inplace=True)
        data.rename(columns={'index': 'Date', 'Date': 'Date'}, inplace=True) # Ensure 'Date' column is named properly

        data['SMA_20'] = data['Close'].rolling(window=20).mean()
        data['SMA_50'] = data['Close'].rolling(window=50).mean()
        data['Daily_Return'] = data['Close'].pct_change()
        data['Volatility_20'] = data['Daily_Return'].rolling(window=20).std()
        data.dropna(inplace=True)
        data.to_csv(csv_path, index=False)
        return data
    except Exception as e:
        print(f"[{ticker}] Fetch Error: {e}")
        return None

def train_engine(data, ticker, dir_path):
    data.reset_index(drop=True, inplace=True)
    
    print(f"[SYSTEM] Engine Training Triggered for {ticker} ({len(data)} Days of Memory)...")
    features = ['Close', 'SMA_20', 'SMA_50', 'Volatility_20']
    X = data[features].iloc[:-1]
    y = data['Daily_Return'].shift(-1).dropna()
    X = X.loc[y.index]
    
    model = xgb.XGBRegressor(n_estimators=1200, learning_rate=0.03, max_depth=8, n_jobs=-1, random_state=42)
    model.fit(X, y)
    
    fitted_returns = model.predict(X)
    data['Hist_Ghost_Price'] = np.nan
    data.loc[X.index + 1, 'Hist_Ghost_Price'] = (X['Close'] * (1 + fitted_returns)).values
    
    compat = max(0, r2_score(y, fitted_returns)) * 100
    
    last_pred = model.predict(data[features].iloc[[-2]])[0]
    actual = data['Daily_Return'].iloc[-1]
    error = abs(last_pred - actual) * 100

    print(f"[{ticker}] >>> COMPATIBILITY FACTOR: {compat:.2f}%")
    if error > 3.0:
        print(f"{BLINK_RED}[{ticker}] ⚠️ HALLUCINATION ALERT! Error Margin: {error:.2f}%{RESET}")
    else:
        print(f"{BOLD_GREEN}[{ticker}] >>> AI LOCK: STABLE. Error: {error:.2f}%{RESET}")

    feat_dict = {f: float(i) for f, i in zip(features, model.feature_importances_)}
    with open(os.path.join(dir_path, "features.json"), 'w') as f: json.dump(feat_dict, f)

    last_feats = data[features].iloc[[-1]].copy()
    current_p = float(last_feats['Close'].iloc[0])
    ghost = []
    for _ in range(7):
        p_ret = float(model.predict(last_feats)[0])
        current_p *= (1 + p_ret)
        ghost.append(current_p)
        last_feats['Close'] = current_p
        
    return ghost, error, compat

def precision_backtest(data, dir_path):
    bt = data.tail(180).copy()
    if 'Hist_Ghost_Price' in bt.columns:
        bt['AI_Return'] = (bt['Hist_Ghost_Price'] - bt['Close'].shift(1)) / bt['Close'].shift(1)
        bt['Signal'] = np.where(bt['AI_Return'] > 0, 1, 0)
    else:
        bt['Signal'] = np.where(bt['SMA_20'] > bt['SMA_50'], 1, 0)
        
    bt['Strat_Return'] = bt['Daily_Return'] * bt['Signal'].shift(1)
    bt['Hold_Equity'] = (1 + bt['Daily_Return']).cumprod() * 10000
    bt['Strategy_Equity'] = (1 + bt['Strat_Return']).cumprod() * 10000
    res = bt[['Date', 'Hold_Equity', 'Strategy_Equity']].dropna()
    res['Date'] = res['Date'].dt.strftime('%Y-%m-%d')
    res.to_csv(os.path.join(dir_path, "backtest.csv"), index=False)

def aladdin_sim(data, dir_path):
    rets = data['Daily_Return'].dropna() * 100
    try:
        res = arch_model(rets, vol='Garch', p=1, q=1).fit(disp='off')
        v = res.conditional_volatility.iloc[-1] / 100
    except Exception as e:
        print(f"[SYSTEM] GARCH model failed to converge. Falling back to simple volatility. Error: {e}")
        v = data['Volatility_20'].iloc[-1]
        if pd.isna(v): v = 0.02
        
    lp = float(data['Close'].iloc[-1])
    paths = np.zeros((252, 1000))
    paths[0] = lp
    for t in range(1, 252):
        paths[t] = paths[t-1] * np.exp((rets.mean()/100 - 0.5*v**2) + v*np.random.standard_normal(1000))
    
    pd.DataFrame(paths[:30]).to_csv(os.path.join(dir_path, "mc.csv"), index=False)
    
    macro = {
        "2008_Crash": [lp * (1 - 0.40 * (i/30)**1.5) for i in range(30)], 
        "Oil_War": [lp * (1 - 0.15 * (i/30)) for i in range(30)],
        "Bubble_Burst": [lp * (1 - 0.25 * (i/30)**0.8) for i in range(30)], 
        "Pandemic": [lp * (1 - 0.30 * np.sin(np.pi * i / 30)) for i in range(30)], 
        "Hyperinflation": [lp * (1 + 0.50 * (i/30)**2) for i in range(30)], 
        "Tech_Boom": [lp * (1 + 0.30 * (i/30)) for i in range(30)]
    }
    
    def sc(d): return {"Extreme_Good": float(np.percentile(paths[d], 95)), "Good": float(np.percentile(paths[d], 75)), "Most_Likely": float(np.mean(paths[d])), "OK": float(np.percentile(paths[d], 50)), "Bad": float(np.percentile(paths[d], 25)), "Extreme_Bad": float(np.percentile(paths[d], 5))}
    return float(np.mean(paths[30] > lp) * 100), v, {"7_Day": sc(7), "1_Month": sc(30), "1_Year": sc(251)}, macro

def calculate_portfolio_weights(lb_data):
    try:
        if not lb_data: return
        vols = [float(item['Vol'].replace('%', '')) for item in lb_data]
        inv = [1 / v if v > 0.001 else 1 for v in vols]
        weights = [{"Asset": item["Asset"], "Weight": f"{(inv[i] / sum(inv)) * 100:.1f}%"} for i, item in enumerate(lb_data)]
        pd.DataFrame(weights).to_csv(os.path.join(DATA_DIR, "portfolio_weights.csv"), index=False)
    except: pass

def run_correlation_guardian():
    try:
        prices = {}
        for root, dirs, files in os.walk(DATA_DIR):
            if "hist.csv" in files:
                ticker = os.path.basename(root)
                df = pd.read_csv(os.path.join(root, "hist.csv"))
                prices[ticker] = df['Daily_Return'].tail(90).values
        if len(prices) > 1:
            df_returns = pd.DataFrame(prices).dropna()
            df_returns.corr().to_csv(os.path.join(DATA_DIR, "correlation_matrix.csv"))
    except: pass

def run_stock_market():
    while True:
        try:
            with open(ASSET_FILE) as f: assets = json.load(f)
        except Exception as e:
            print(f"{BLINK_RED}[SYSTEM] Failed to read {ASSET_FILE}: {e}{RESET}")
            time.sleep(60)
            continue

        # Check Indian Market Timings (9:15 AM to 3:30 PM IST, Mon-Fri)
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        
        is_weekend = now_ist.weekday() >= 5
        market_open_time = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close_time = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        
        is_market_open = not is_weekend and (market_open_time <= now_ist <= market_close_time)
        
        if not is_market_open:
            print(f"{CYAN}[SYSTEM] Indian Market is currently CLOSED (Current IST: {now_ist.strftime('%H:%M:%S')}). Waiting for market to open...{RESET}")
            time.sleep(1800) # Sleep for 30 minutes before checking again
            # We still allow one initial fetch even if closed, to ensure offline data exists.
            # But let's just proceed to fetch offline data once and then block? 
            # Actually, if we just sleep here, it won't fetch anything. Let's make it smarter:
            # We will still process assets to ensure offline files exist, but we won't re-fetch from yfinance if we already have today's offline data.

        lb = []
        for cat, tks in assets.items():
            for tk in tks:
                dp = os.path.join(DATA_DIR, tk)
                os.makedirs(dp, exist_ok=True)
                
                prev_date = None
                hist_path = os.path.join(dp, "hist.csv")
                if os.path.exists(hist_path):
                    try:
                        prev_df = pd.read_csv(hist_path)
                        prev_date = str(prev_df['Date'].iloc[-1])
                    except:
                        pass

                data = fetch_and_store_data(tk, dp)
                
                if data is not None:
                    curr_date = str(data['Date'].iloc[-1])
                    
                    if prev_date == curr_date and os.path.exists(os.path.join(dp, "pred.json")):
                        print(f"[{tk}] Data unchanged (Last: {curr_date}). Skipping AI Retraining.")
                        
                        # Just append the old data to leaderboard and skip training
                        try:
                            with open(os.path.join(dp, "pred.json")) as f: rep = json.load(f)
                            lb.append({"Asset": tk, "Price": f"₹{rep['Price']:,.2f}", "Signal": rep['Signal'], "Vol": f"{rep['Vol']*100:.2f}%", "Prob": f"{rep['Prob']:.1f}%"})
                        except: pass
                        continue
                        
                    ghost, err, comp = train_engine(data, tk, dp)
                    precision_backtest(data, dp)
                    prob, vol, scn, mcr = aladdin_sim(data, dp)
                    
                    market_mode = "BULL 🐂" if float(data['Close'].iloc[-1]) > float(data['SMA_50'].iloc[-1]) else "BEAR 🐻"
                    pr = ((ghost[-1] - float(data['Close'].iloc[-1])) / float(data['Close'].iloc[-1])) * 100
                    sig = "STRONG BUY 🟢" if pr > 5 else "BUY ↗️" if pr > 1.5 else "STRONG SELL 🔴" if pr < -5 else "SELL ↘️" if pr < -1.5 else "HOLD ➖"

                    verdict = f"Algorithmic Audit: Model exhibits {comp:.1f}% historical compatibility with a {err:.2f}% error margin. 7-Day projection is {'BULLISH' if pr > 0 else 'BEARISH'} ({pr:+.2f}%). Volatility stands at {vol*100:.1f}%, suggesting a {market_mode.split()[0]} environment."

                    rep = {
                        "Price": float(data['Close'].iloc[-1]), "Signal": sig, "Ghost": ghost, 
                        "Scenarios": scn, "Macro": mcr, "Verdict": verdict, "Compat": comp, 
                        "Error": err, "Vol": vol, "Prob": prob, "Market_Mode": market_mode, "Vol_Stop": float(data['Close'].iloc[-1]) * (1 - (vol * 1.5))
                    }
                    with open(os.path.join(dp, "pred.json"), 'w') as f: json.dump(rep, f)
                    data.to_csv(os.path.join(dp, "hist.csv"), index=False)
                    lb.append({"Asset": tk, "Price": f"₹{rep['Price']:,.2f}", "Signal": sig, "Vol": f"{vol*100:.2f}%", "Prob": f"{prob:.1f}%"})
        
        pd.DataFrame(lb).to_csv(os.path.join(DATA_DIR, "lb.csv"), index=False)
        calculate_portfolio_weights(lb)
        run_correlation_guardian()
        
        print(f"\n{BOLD_GREEN}[{datetime.now().strftime('%H:%M:%S')}] Hourly Cycle Complete. Sleeping for 60 Minutes...{RESET}")
        time.sleep(3600)

if __name__ == "__main__": 
    run_stock_market()
