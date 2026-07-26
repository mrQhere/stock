import yfinance as yf
import pandas as pd
import numpy as np
import xgboost as xgb
from arch import arch_model
from sklearn.metrics import r2_score
import json, os, time, warnings, logging
from datetime import datetime
import pytz

warnings.filterwarnings('ignore')

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data_lake")
ASSET_FILE = os.path.join(BASE_DIR, "assets.json")
LOG_FILE  = os.path.join(BASE_DIR, "picks.log")

# ── ANSI palette ───────────────────────────────────────────────────────────────
BLINK_RED   = '\033[5;31m'
BOLD_GREEN  = '\033[1;32m'
CYAN        = '\033[0;36m'
YELLOW      = '\033[0;33m'
RESET       = '\033[0m'

# ── Structured logger ──────────────────────────────────────────────────────────
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ── Category → folder map ──────────────────────────────────────────────────────
ASSET_CATEGORY_MAP = {
    "stocks": "stocks",
    "etfs": "etfs",
    "indices": "indices",
    "mutual_funds": "mutual_funds",
}

def asset_dir(asset_type: str, ticker: str) -> str:
    """Return and auto-create: data_lake/<type>/<ticker>/"""
    path = os.path.join(DATA_DIR, ASSET_CATEGORY_MAP.get(asset_type, asset_type), ticker.replace("^", "IDX_"))
    os.makedirs(path, exist_ok=True)
    return path

# ── Data fetch ─────────────────────────────────────────────────────────────────
def fetch_and_store(ticker: str, dir_path: str) -> pd.DataFrame | None:
    print(f"\n{CYAN}[{ticker}] Syncing 5Y data from Yahoo Finance...{RESET}")
    try:
        raw = yf.Ticker(ticker).history(period="5y", auto_adjust=True)
        if raw is None or raw.empty:
            print(f"[{ticker}] No data returned."); return None

        raw.index = raw.index.tz_localize(None)
        raw.reset_index(inplace=True)
        raw.rename(columns={"index": "Date", "Date": "Date"}, inplace=True)

        # ── Technical indicators ───────────────────────────────────────────────
        raw['SMA_20']      = raw['Close'].rolling(20).mean()
        raw['SMA_50']      = raw['Close'].rolling(50).mean()
        raw['SMA_200']     = raw['Close'].rolling(200).mean()
        raw['EMA_12']      = raw['Close'].ewm(span=12).mean()
        raw['EMA_26']      = raw['Close'].ewm(span=26).mean()
        raw['MACD']        = raw['EMA_12'] - raw['EMA_26']
        raw['Daily_Return']= raw['Close'].pct_change()
        raw['Volatility_20']= raw['Daily_Return'].rolling(20).std()

        # RSI
        delta = raw['Close'].diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, np.nan)
        raw['RSI'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        raw['BB_Std'] = raw['Close'].rolling(20).std()
        raw['BB_Upper'] = raw['SMA_20'] + (raw['BB_Std'] * 2)
        raw['BB_Lower'] = raw['SMA_20'] - (raw['BB_Std'] * 2)
        raw['BB_Width'] = (raw['BB_Upper'] - raw['BB_Lower']) / raw['SMA_20']
        raw['BB_PB'] = (raw['Close'] - raw['BB_Lower']) / (raw['BB_Upper'] - raw['BB_Lower']).replace(0, np.nan)

        # Average True Range (ATR)
        high_low = raw['High'] - raw['Low']
        high_close = (raw['High'] - raw['Close'].shift()).abs()
        low_close = (raw['Low'] - raw['Close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        raw['ATR_14'] = true_range.rolling(14).mean()

        # Stochastic Oscillator
        low_14 = raw['Low'].rolling(14).min()
        high_14 = raw['High'].rolling(14).max()
        raw['Stoch_K'] = 100 * ((raw['Close'] - low_14) / (high_14 - low_14).replace(0, np.nan))
        raw['Stoch_D'] = raw['Stoch_K'].rolling(3).mean()
        
        # 52-Week High / Low (approx 252 trading days)
        raw['High_52W'] = raw['High'].rolling(252).max()
        raw['Low_52W'] = raw['Low'].rolling(252).min()

        raw.dropna(inplace=True)
        raw.to_csv(os.path.join(dir_path, "hist.csv"), index=False)
        return raw
    except Exception as e:
        print(f"[{ticker}] Fetch error: {e}"); return None

# ── XGBoost training ───────────────────────────────────────────────────────────
def train_engine(data: pd.DataFrame, ticker: str, dir_path: str):
    data.reset_index(drop=True, inplace=True)
    features = ['Close', 'SMA_20', 'SMA_50', 'SMA_200', 'MACD', 'RSI', 'Volatility_20', 'BB_Width', 'BB_PB', 'ATR_14', 'Stoch_K', 'Stoch_D']
    X = data[features].iloc[:-1]
    y = data['Daily_Return'].shift(-1).dropna()
    X = X.loc[y.index]

    model = xgb.XGBRegressor(n_estimators=1200, learning_rate=0.03, max_depth=8,
                              subsample=0.8, colsample_bytree=0.8,
                              n_jobs=-1, random_state=42)
    model.fit(X, y)

    fitted = model.predict(X)
    data['Hist_Ghost_Price'] = np.nan
    data.loc[X.index + 1, 'Hist_Ghost_Price'] = (X['Close'] * (1 + fitted)).values

    compat = max(0, r2_score(y, fitted)) * 100
    last_pred = model.predict(data[features].iloc[[-2]])[0]
    actual    = data['Daily_Return'].iloc[-1]
    error     = abs(last_pred - actual) * 100

    feat_dict = {f: float(i) for f, i in zip(features, model.feature_importances_)}
    with open(os.path.join(dir_path, "features.json"), 'w') as f: json.dump(feat_dict, f)

    last_feats  = data[features].iloc[[-1]].copy()
    current_p   = float(last_feats['Close'].iloc[0])
    ghost_7d    = []
    for _ in range(7):
        p_ret = float(model.predict(last_feats)[0])
        current_p *= (1 + p_ret)
        ghost_7d.append(current_p)
        last_feats['Close'] = current_p

    print(f"[{ticker}] Compat={compat:.1f}%  Error={error:.2f}%")
    return ghost_7d, error, compat, feat_dict

# ── Backtest ───────────────────────────────────────────────────────────────────
def precision_backtest(data: pd.DataFrame, dir_path: str):
    bt = data.tail(180).copy()
    if 'Hist_Ghost_Price' in bt.columns:
        bt['AI_Return'] = (bt['Hist_Ghost_Price'] - bt['Close'].shift(1)) / bt['Close'].shift(1)
        bt['Signal']    = np.where(bt['AI_Return'] > 0, 1, 0)
    else:
        bt['Signal'] = np.where(bt['SMA_20'] > bt['SMA_50'], 1, 0)

    bt['Strat_Return']   = bt['Daily_Return'] * bt['Signal'].shift(1)
    bt['Hold_Equity']    = (1 + bt['Daily_Return']).cumprod() * 100000
    bt['Strategy_Equity']= (1 + bt['Strat_Return']).cumprod() * 100000
    res = bt[['Date','Hold_Equity','Strategy_Equity']].dropna()
    res['Date'] = res['Date'].dt.strftime('%Y-%m-%d')
    res.to_csv(os.path.join(dir_path, "backtest.csv"), index=False)
    
    # Sharpe & max drawdown
    strat_ret = bt['Strat_Return'].dropna()
    sharpe = (strat_ret.mean() / strat_ret.std()) * np.sqrt(252) if strat_ret.std() > 0 else 0
    roll_max = bt['Strategy_Equity'].cummax()
    max_dd = ((bt['Strategy_Equity'] - roll_max) / roll_max).min() * 100
    return float(sharpe), float(max_dd)

# ── Monte Carlo / GARCH ────────────────────────────────────────────────────────
def monte_carlo_sim(data: pd.DataFrame, dir_path: str):
    rets = data['Daily_Return'].dropna() * 100
    try:
        res = arch_model(rets, vol='Garch', p=1, q=1).fit(disp='off')
        v   = res.conditional_volatility.iloc[-1] / 100
    except:
        v = data['Volatility_20'].iloc[-1]
        if pd.isna(v): v = 0.02

    lp    = float(data['Close'].iloc[-1])
    mu    = rets.mean() / 100
    paths = np.zeros((252, 1000))
    paths[0] = lp
    for t in range(1, 252):
        shocks   = v * np.random.standard_normal(1000)
        paths[t] = paths[t-1] * np.exp((mu - 0.5*v**2) + shocks)

    pd.DataFrame(paths[:30]).to_csv(os.path.join(dir_path, "mc.csv"), index=False)

    macro = {
        "2008_Crash":   [lp*(1 - 0.40*(i/30)**1.5) for i in range(30)],
        "Oil_War":      [lp*(1 - 0.15*(i/30))       for i in range(30)],
        "Bubble_Burst": [lp*(1 - 0.25*(i/30)**0.8)  for i in range(30)],
        "Pandemic":     [lp*(1 - 0.30*np.sin(np.pi*i/30)) for i in range(30)],
        "Hyperinflation":[lp*(1 + 0.50*(i/30)**2)   for i in range(30)],
        "Tech_Boom":    [lp*(1 + 0.30*(i/30))        for i in range(30)],
    }

    def sc(d):
        return {k: float(np.percentile(paths[d], p)) for k, p in
                [("Extreme_Good",95),("Good",75),("Most_Likely",50),("Bad",25),("Extreme_Bad",5)]}

    prob_up = float(np.mean(paths[30] > lp) * 100)
    scenarios = {"7_Day": sc(7), "1_Month": sc(30), "1_Year": sc(251)}
    return prob_up, v, scenarios, macro

# ── Portfolio weights ──────────────────────────────────────────────────────────
def calculate_portfolio_weights(lb_data):
    try:
        if not lb_data: return
        vols   = [float(item['Vol'].replace('%','')) for item in lb_data]
        inv    = [1/v if v > 0.001 else 1 for v in vols]
        total  = sum(inv)
        weights = [{"Asset": item["Asset"], "Category": item.get("Category","—"),
                    "Weight_pct": round((inv[i]/total)*100, 2)} for i, item in enumerate(lb_data)]
        pd.DataFrame(weights).to_csv(os.path.join(DATA_DIR, "portfolio_weights.csv"), index=False)
    except: pass

# ── Correlation matrix ─────────────────────────────────────────────────────────
def run_correlation_guardian():
    try:
        prices = {}
        for root, dirs, files in os.walk(DATA_DIR):
            if "hist.csv" in files:
                ticker = os.path.basename(root)
                df = pd.read_csv(os.path.join(root, "hist.csv"))
                if 'Daily_Return' in df.columns:
                    prices[ticker] = df['Daily_Return'].tail(90).values
        if len(prices) > 1:
            df_r = pd.DataFrame(prices).dropna()
            df_r.corr().to_csv(os.path.join(DATA_DIR, "correlation_matrix.csv"))
    except: pass

# ── Build "why" rationale log ──────────────────────────────────────────────────
def build_rationale(ticker, signal, compat, error, vol, prob, sharpe, max_dd, feat_dict, price, pr):
    top_feat   = max(feat_dict, key=feat_dict.get) if feat_dict else "N/A"
    strength   = "HIGH" if compat > 70 else "MODERATE" if compat > 50 else "LOW"
    risk_label = "LOW RISK" if abs(max_dd) < 10 else "MODERATE RISK" if abs(max_dd) < 20 else "HIGH RISK"

    rationale = (
        f"SIGNAL: {signal} | PRICE: ₹{price:,.2f} | 7D PROJECTION: {pr:+.2f}%\n"
        f"  → Model Strength   : {strength} (R² compat={compat:.1f}%, error={error:.2f}%)\n"
        f"  → Dominant Driver  : {top_feat} (importance={feat_dict.get(top_feat,0):.3f})\n"
        f"  → GARCH Volatility : {vol*100:.2f}% daily | Upside Probability: {prob:.1f}%\n"
        f"  → Sharpe Ratio     : {sharpe:.2f} | Max Drawdown: {max_dd:.2f}%\n"
        f"  → Risk Profile     : {risk_label}"
    )
    logging.info(f"[{ticker}]\n{rationale}")
    return rationale

# ── Master run loop ────────────────────────────────────────────────────────────
def run_stock_market():
    os.makedirs(DATA_DIR, exist_ok=True)

    while True:
        try:
            with open(ASSET_FILE) as f: assets = json.load(f)
        except Exception as e:
            print(f"{BLINK_RED}[SYSTEM] Cannot read assets.json: {e}{RESET}")
            time.sleep(60); continue

        # ── Indian market hours check ──────────────────────────────────────────
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        is_weekend   = now.weekday() >= 5
        mkt_open     = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        mkt_close    = now.replace(hour=15, minute=30, second=0, microsecond=0)
        market_live  = not is_weekend and (mkt_open <= now <= mkt_close)

        status_str   = f"{BOLD_GREEN}LIVE{RESET}" if market_live else f"{YELLOW}CLOSED{RESET}"
        print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S IST')}] NSE Market: {status_str}")

        lb = []
        for asset_type, subcats in assets.items():
            for subcat, tickers in subcats.items():
                for tk in tickers:
                    dp = asset_dir(asset_type, tk)
                    hist_path = os.path.join(dp, "hist.csv")
                    pred_path = os.path.join(dp, "pred.json")

                    # Check if we already have today's data
                    prev_date = None
                    if os.path.exists(hist_path):
                        try:
                            prev_date = str(pd.read_csv(hist_path)['Date'].iloc[-1])
                        except: pass

                    data = fetch_and_store(tk, dp)
                    if data is None: continue

                    curr_date = str(data['Date'].iloc[-1])

                    # Skip heavy retraining if data unchanged
                    if prev_date == curr_date and os.path.exists(pred_path):
                        print(f"[{tk}] Unchanged ({curr_date}). Serving cached prediction.")
                        try:
                            rep = json.load(open(pred_path))
                            lb.append({"Asset": tk, "Category": f"{asset_type}/{subcat}",
                                       "Price": f"₹{rep['Price']:,.2f}",
                                       "Signal": rep['Signal'], "Vol": f"{rep['Vol']*100:.2f}%",
                                       "Prob": f"{rep['Prob']:.1f}%", "Sharpe": f"{rep.get('Sharpe',0):.2f}"})
                        except: pass
                        continue

                    # ── Heavy compute ──────────────────────────────────────────
                    try:
                        ghost, err, comp, feats = train_engine(data, tk, dp)
                        sharpe, max_dd          = precision_backtest(data, dp)
                        prob, vol, scn, mcr     = monte_carlo_sim(data, dp)

                        price = float(data['Close'].iloc[-1])
                        
                        # ── Investing Tools Calculation ──
                        years = (data['Date'].iloc[-1] - data['Date'].iloc[0]).days / 365.25
                        cagr = ((price / float(data['Close'].iloc[0])) ** (1/years) - 1) * 100 if years > 0 else 0
                        
                        downside_returns = data['Daily_Return'][data['Daily_Return'] < 0]
                        downside_std = downside_returns.std() * np.sqrt(252)
                        ann_ret = data['Daily_Return'].mean() * 252
                        sortino = float(ann_ret / downside_std) if downside_std > 0 else 0
                        
                        var_95 = float(np.percentile(data['Daily_Return'].dropna(), 5)) * 100
                        
                        sma50 = float(data['SMA_50'].iloc[-1])
                        sma200 = float(data['SMA_200'].iloc[-1])
                        golden_cross = "Golden Cross 🐂" if sma50 > sma200 else "Death Cross 🐻"
                        
                        high_52 = float(data['High_52W'].iloc[-1])
                        low_52 = float(data['Low_52W'].iloc[-1])
                        dist_high = ((price - high_52) / high_52) * 100 if high_52 > 0 else 0
                        dist_low = ((price - low_52) / low_52) * 100 if low_52 > 0 else 0

                        pr    = ((ghost[-1] - price) / price) * 100
                        sig   = ("STRONG BUY 🟢"  if pr >  5 else
                                 "BUY ↗️"          if pr >  1.5 else
                                 "STRONG SELL 🔴"  if pr < -5 else
                                 "SELL ↘️"          if pr < -1.5 else "HOLD ➖")

                        market_mode = "BULL 🐂" if price > float(data['SMA_50'].iloc[-1]) else "BEAR 🐻"
                        rationale   = build_rationale(tk, sig, comp, err, vol, prob,
                                                      sharpe, max_dd, feats, price, pr)

                        rep = {
                            "Ticker": tk, "Category": asset_type, "Subcategory": subcat,
                            "Price": price, "Signal": sig, "Ghost": ghost,
                            "Scenarios": scn, "Macro": mcr,
                            "Rationale": rationale, "Compat": comp, "Error": err,
                            "Vol": vol, "Prob": prob, "Sharpe": sharpe, "MaxDD": max_dd,
                            "Market_Mode": market_mode,
                            "Technical_Indicators": {
                                "RSI": float(data['RSI'].iloc[-1]),
                                "MACD": float(data['MACD'].iloc[-1]),
                                "BB_PB": float(data['BB_PB'].iloc[-1]),
                                "ATR_14": float(data['ATR_14'].iloc[-1]),
                                "Stoch_K": float(data['Stoch_K'].iloc[-1])
                            },
                            "Investing_Tools": {
                                "CAGR": cagr,
                                "Sortino": sortino,
                                "VaR_95": var_95,
                                "Golden_Cross": golden_cross,
                                "Dist_52W_High": dist_high,
                                "Dist_52W_Low": dist_low,
                                "High_52W": high_52,
                                "Low_52W": low_52
                            },
                            "Vol_Stop": price * (1 - vol * 1.5),
                            "Last_Updated": now.strftime('%Y-%m-%d %H:%M IST'),
                        }
                        with open(pred_path, 'w') as f: json.dump(rep, f)
                        data.to_csv(hist_path, index=False)

                        lb.append({"Asset": tk, "Category": f"{asset_type}/{subcat}",
                                   "Price": f"₹{price:,.2f}", "Signal": sig,
                                   "Vol": f"{vol*100:.2f}%", "Prob": f"{prob:.1f}%",
                                   "Sharpe": f"{sharpe:.2f}", "MaxDD": f"{max_dd:.2f}%"})

                    except Exception as ex:
                        print(f"{BLINK_RED}[{tk}] Compute error: {ex}{RESET}")

        # ── Aggregate outputs ──────────────────────────────────────────────────
        if lb:
            pd.DataFrame(lb).to_csv(os.path.join(DATA_DIR, "lb.csv"), index=False)
            calculate_portfolio_weights(lb)
            run_correlation_guardian()

        wait = 3600 if market_live else 1800
        print(f"\n{BOLD_GREEN}[{now.strftime('%H:%M:%S')}] Cycle complete. Next check in {wait//60}m.{RESET}")
        time.sleep(wait)

if __name__ == "__main__":
    run_stock_market()
