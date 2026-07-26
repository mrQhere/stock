import yfinance as yf
import pandas as pd
import numpy as np
import xgboost as xgb
from arch import arch_model
from sklearn.metrics import r2_score
import json, os, time, warnings, logging, sqlite3
from datetime import datetime
import pytz

import torch
import torch.nn as nn
import torch.optim as optim
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

warnings.filterwarnings('ignore')

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data_lake")
ASSET_FILE = os.path.join(BASE_DIR, "assets.json")
LOG_FILE  = os.path.join(BASE_DIR, "picks.log")
DB_PATH   = os.path.join(DATA_DIR, "quant.db")
HYPERPARAMS_FILE = os.path.join(DATA_DIR, "hyperparams.json")

BLINK_RED   = '\033[5;31m'
BOLD_GREEN  = '\033[1;32m'
CYAN        = '\033[0;36m'
YELLOW      = '\033[0;33m'
RESET       = '\033[0m'

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS historical_data 
                 (Ticker TEXT, Date TEXT, Open REAL, High REAL, Low REAL, Close REAL, Volume REAL, Dividends REAL, 
                 SMA_20 REAL, SMA_50 REAL, SMA_200 REAL, EMA_12 REAL, EMA_26 REAL, MACD REAL, Daily_Return REAL, Volatility_20 REAL,
                 RSI REAL, BB_Std REAL, BB_Upper REAL, BB_Lower REAL, BB_Width REAL, BB_PB REAL, ATR_14 REAL, Stoch_K REAL, Stoch_D REAL,
                 High_52W REAL, Low_52W REAL, Hist_Ghost_Price REAL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS predictions 
                 (Ticker TEXT PRIMARY KEY, Category TEXT, Subcategory TEXT, Price REAL, Signal TEXT, 
                  Prob REAL, Sharpe REAL, MaxDD REAL, Vol REAL, Market_Mode TEXT, JSON_Blob TEXT)''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS leaderboard 
                 (Asset TEXT PRIMARY KEY, Category TEXT, Price TEXT, Signal TEXT, Vol TEXT, Prob TEXT, Sharpe TEXT, MaxDD TEXT)''')
                 
    c.execute('''CREATE TABLE IF NOT EXISTS backtests 
                 (Ticker TEXT, Date TEXT, Hold_Equity REAL, Strategy_Equity REAL)''')
                 
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio_weights 
                 (Asset TEXT PRIMARY KEY, Category TEXT, Weight_pct REAL)''')
                 
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio_trades 
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT, Ticker TEXT, Quantity REAL, Buy_Price REAL, Trade_Date TEXT)''')
    
    conn.commit()
    return conn

def fetch_and_store(ticker: str, conn: sqlite3.Connection) -> pd.DataFrame | None:
    print(f"\n{CYAN}[{ticker}] Syncing 5Y data from Yahoo Finance...{RESET}")
    try:
        raw = yf.Ticker(ticker).history(period="5y", auto_adjust=True)
        if raw is None or raw.empty: return None

        raw.index = raw.index.tz_localize(None)
        raw.reset_index(inplace=True)
        raw.rename(columns={"index": "Date", "Date": "Date"}, inplace=True)
        raw['Ticker'] = ticker
        if 'Dividends' not in raw.columns: raw['Dividends'] = 0.0

        raw['SMA_20'] = raw['Close'].rolling(20).mean()
        raw['SMA_50'] = raw['Close'].rolling(50).mean()
        raw['SMA_200'] = raw['Close'].rolling(200).mean()
        raw['EMA_12'] = raw['Close'].ewm(span=12).mean()
        raw['EMA_26'] = raw['Close'].ewm(span=26).mean()
        raw['MACD'] = raw['EMA_12'] - raw['EMA_26']
        raw['Daily_Return'] = raw['Close'].pct_change()
        raw['Volatility_20'] = raw['Daily_Return'].rolling(20).std()

        delta = raw['Close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        raw['RSI'] = 100 - (100 / (1 + rs))

        raw['BB_Std'] = raw['Close'].rolling(20).std()
        raw['BB_Upper'] = raw['SMA_20'] + (raw['BB_Std'] * 2)
        raw['BB_Lower'] = raw['SMA_20'] - (raw['BB_Std'] * 2)
        raw['BB_Width'] = (raw['BB_Upper'] - raw['BB_Lower']) / raw['SMA_20']
        raw['BB_PB'] = (raw['Close'] - raw['BB_Lower']) / (raw['BB_Upper'] - raw['BB_Lower']).replace(0, np.nan)

        high_low = raw['High'] - raw['Low']
        high_close = (raw['High'] - raw['Close'].shift()).abs()
        low_close = (raw['Low'] - raw['Close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        raw['ATR_14'] = true_range.rolling(14).mean()

        low_14 = raw['Low'].rolling(14).min()
        high_14 = raw['High'].rolling(14).max()
        raw['Stoch_K'] = 100 * ((raw['Close'] - low_14) / (high_14 - low_14).replace(0, np.nan))
        raw['Stoch_D'] = raw['Stoch_K'].rolling(3).mean()
        
        raw['High_52W'] = raw['High'].rolling(252).max()
        raw['Low_52W'] = raw['Low'].rolling(252).min()
        raw['Hist_Ghost_Price'] = np.nan

        raw.dropna(inplace=True)
        return raw
    except Exception as e:
        print(f"[{ticker}] Fetch error: {e}"); return None

# ── LSTM Model ──
class LSTMPredictor(nn.Module):
    def __init__(self, input_size, hidden_layer_size=50, output_size=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_layer_size, batch_first=True)
        self.linear = nn.Linear(hidden_layer_size, output_size)

    def forward(self, input_seq):
        lstm_out, _ = self.lstm(input_seq)
        return self.linear(lstm_out[:, -1, :])

def train_lstm(X, y):
    try:
        X_mean, X_std = X.mean(), X.std().replace(0, 1)
        X_scaled = (X - X_mean) / X_std
        y_mean, y_std = y.mean(), y.std()
        if y_std == 0: y_std = 1
        y_scaled = (y - y_mean) / y_std

        seq_length = 5
        X_seq, y_seq = [], []
        for i in range(len(X_scaled) - seq_length):
            X_seq.append(X_scaled.iloc[i:i+seq_length].values)
            y_seq.append(y_scaled.iloc[i+seq_length])
            
        if len(X_seq) < 100: return None, None
            
        X_t = torch.FloatTensor(np.array(X_seq))
        y_t = torch.FloatTensor(np.array(y_seq)).view(-1, 1)

        train_size = int(len(X_t) * 0.8)
        X_train, X_val = X_t[:train_size], X_t[train_size:]
        y_train, y_val = y_t[:train_size], y_t[train_size:]

        model = LSTMPredictor(X.shape[1])
        optimizer = optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        for epoch in range(40):
            model.train()
            optimizer.zero_grad()
            loss = criterion(model(X_train), y_train)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            val_preds = model(X_val).numpy() * y_std + y_mean
            y_val_np = y_val.numpy() * y_std + y_mean
            r2 = max(0, r2_score(y_val_np, val_preds)) * 100

            last_seq = X_t[-1:].clone()
            ghost_7d = []
            current_p = float(X.iloc[-1]['Close'])
            
            for _ in range(7):
                p_ret = model(last_seq).item() * y_std + y_mean
                p_ret = max(min(p_ret, 0.1), -0.1) # clip
                current_p *= (1 + p_ret)
                ghost_7d.append(current_p)
                
                new_row = last_seq[0, -1, :].clone()
                new_row[0] = (current_p - X_mean['Close']) / X_std['Close']
                last_seq = torch.cat((last_seq[:, 1:, :], new_row.view(1, 1, -1)), dim=1)
                
        return ghost_7d, float(r2)
    except: return None, None

def train_engine(data: pd.DataFrame, ticker: str, hyperparams: dict):
    data.reset_index(drop=True, inplace=True)
    features = ['Close', 'SMA_20', 'SMA_50', 'SMA_200', 'MACD', 'RSI', 'Volatility_20', 'BB_Width', 'BB_PB', 'ATR_14', 'Stoch_K', 'Stoch_D']
    X = data[features].iloc[:-1]
    y = data['Daily_Return'].shift(-1).dropna()
    X = X.loc[y.index]

    train_size = int(len(X) * 0.8) if len(X) >= 160 else len(X) - 60
    X_train, X_holdout = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_holdout = y.iloc[:train_size], y.iloc[train_size:]

    params = hyperparams.get(ticker, {
        'n_estimators': 1200, 'learning_rate': 0.03, 'max_depth': 8,
        'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 42, 'n_jobs': -1
    })
    model = xgb.XGBRegressor(**params)
    model.fit(X_train, y_train)

    holdout_r2 = max(0, r2_score(y_holdout, model.predict(X_holdout))) * 100
    data.loc[X.index + 1, 'Hist_Ghost_Price'] = (X['Close'] * (1 + model.predict(X))).values
    
    error = abs(model.predict(X.iloc[[-1]])[0] - data['Daily_Return'].iloc[-1]) * 100
    feat_dict = {f: float(i) for f, i in zip(features, model.feature_importances_)}

    current_p = float(X.iloc[-1]['Close'])
    last_feats = X.iloc[[-1]].copy()
    ghost_7d_xgb = []
    
    train_std = y_train.std()
    ret_clip_min, ret_clip_max = -3 * train_std, 3 * train_std

    for _ in range(7):
        p_ret = max(min(float(model.predict(last_feats)[0]), ret_clip_max), ret_clip_min)
        current_p *= (1 + p_ret)
        ghost_7d_xgb.append(current_p)
        last_feats['Close'] = current_p

    # Train LSTM
    ghost_7d_lstm, lstm_r2 = train_lstm(X, y)

    return ghost_7d_xgb, ghost_7d_lstm, float(error), holdout_r2, lstm_r2, feat_dict, data

def precision_backtest(data, ticker, conn):
    bt = data.tail(180).copy()
    bt['Signal'] = np.where((bt['Hist_Ghost_Price'] - bt['Close'].shift(1)) > 0, 1, 0) if 'Hist_Ghost_Price' in bt.columns else np.where(bt['SMA_20'] > bt['SMA_50'], 1, 0)
    bt['Strat_Return'] = bt['Daily_Return'] * bt['Signal'].shift(1)
    bt['Hold_Equity'] = (1 + bt['Daily_Return']).cumprod() * 100000
    bt['Strategy_Equity'] = (1 + bt['Strat_Return']).cumprod() * 100000
    
    res = bt[['Ticker', 'Date','Hold_Equity','Strategy_Equity']].dropna()
    res['Date'] = res['Date'].dt.strftime('%Y-%m-%d')
    conn.execute("DELETE FROM backtests WHERE Ticker = ?", (ticker,))
    res.to_sql("backtests", conn, if_exists="append", index=False)
    
    strat_ret = bt['Strat_Return'].dropna()
    sharpe = (strat_ret.mean() / strat_ret.std()) * np.sqrt(252) if strat_ret.std() > 0 else 0
    roll_max = bt['Strategy_Equity'].cummax()
    max_dd = ((bt['Strategy_Equity'] - roll_max) / roll_max).min() * 100
    return float(sharpe), float(max_dd)

def get_sentiment(ticker):
    try:
        news = yf.Ticker(ticker).news
        analyzer = SentimentIntensityAnalyzer()
        scores = [analyzer.polarity_scores(n['title'])['compound'] for n in news if 'title' in n]
        return float(sum(scores)/len(scores)) if scores else 0.0
    except: return 0.0

def get_factors(ticker, df):
    try:
        info = yf.Ticker(ticker).info
        mc = info.get('marketCap', 0)
        pb = info.get('priceToBook', 0)
        mom = ((df['Close'].iloc[-1] - df['Close'].iloc[-126]) / df['Close'].iloc[-126] * 100) if len(df) > 126 else 0.0
        return mc, pb, mom
    except: return 0, 0, 0.0

def monte_carlo_sim(data: pd.DataFrame, ticker: str):
    rets = data['Daily_Return'].dropna() * 100
    try:
        v = arch_model(rets, vol='Garch', p=1, q=1).fit(disp='off').conditional_volatility.iloc[-1] / 100
    except:
        v = data['Volatility_20'].iloc[-1] if not pd.isna(data['Volatility_20'].iloc[-1]) else 0.02

    lp, mu = float(data['Close'].iloc[-1]), rets.mean() / 100
    paths = np.zeros((252, 1000)); paths[0] = lp
    for t in range(1, 252):
        paths[t] = paths[t-1] * np.exp((mu - 0.5*v**2) + v * np.random.standard_normal(1000))

    mc_paths = [paths[:30, i].tolist() for i in range(50)]
    macro = {
        "2008_Crash":   [lp*(1 - 0.40*(i/30)**1.5) for i in range(30)],
        "Oil_War":      [lp*(1 - 0.15*(i/30))       for i in range(30)],
        "Bubble_Burst": [lp*(1 - 0.25*(i/30)**0.8)  for i in range(30)],
        "Pandemic":     [lp*(1 - 0.30*np.sin(np.pi*i/30)) for i in range(30)],
        "Hyperinflation":[lp*(1 + 0.50*(i/30)**2)   for i in range(30)],
        "Tech_Boom":    [lp*(1 + 0.30*(i/30))        for i in range(30)],
    }

    def sc(d): return {k: float(np.percentile(paths[d], p)) for k, p in [("Extreme_Good",95),("Good",75),("Most_Likely",50),("Bad",25),("Extreme_Bad",5)]}
    prob_up = float(np.mean(paths[30] > lp) * 100)
    return prob_up, v, {"7_Day": sc(7), "1_Month": sc(30), "1_Year": sc(251)}, macro, mc_paths

def generate_signal(pr: float, sharpe: float, max_dd: float, market_mode: str, sentiment: float) -> str:
    if pr > 5 and sentiment > 0: sig = "STRONG BUY 🟢"
    elif pr > 1.5: sig = "BUY ↗️"
    elif pr < -5 and sentiment < 0: sig = "STRONG SELL 🔴"
    elif pr < -1.5: sig = "SELL ↘️"
    else: sig = "HOLD ➖"

    if "BEAR" in market_mode and sharpe < 0 and "BUY" in sig: sig = "HOLD ➖"
    return sig

def calculate_portfolio_weights(lb_data, conn):
    try:
        if not lb_data: return
        vols = [float(item['Vol'].replace('%','')) for item in lb_data]
        inv = [1/v if v > 0.001 else 1 for v in vols]
        total = sum(inv)
        weights = [{"Asset": item["Asset"], "Category": item.get("Category","—"), "Weight_pct": round((inv[i]/total)*100, 2)} for i, item in enumerate(lb_data)]
        conn.execute("DELETE FROM portfolio_weights")
        pd.DataFrame(weights).to_sql("portfolio_weights", conn, if_exists="append", index=False)
    except: pass

def run_stock_market():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = init_db()
    hyperparams = {}
    if os.path.exists(HYPERPARAMS_FILE):
        try:
            with open(HYPERPARAMS_FILE, 'r') as f: hyperparams = json.load(f)
        except: pass

    while True:
        try:
            with open(ASSET_FILE) as f: assets = json.load(f)
        except: time.sleep(60); continue

        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        is_weekend = now.weekday() >= 5
        mkt_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        mkt_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        market_live = not is_weekend and (mkt_open <= now <= mkt_close)

        print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S IST')}] Market: {'LIVE' if market_live else 'CLOSED'}")

        lb = []
        for asset_type, subcats in assets.items():
            for subcat, tickers in subcats.items():
                for tk in tickers:
                    try:
                        row = conn.execute("SELECT Date FROM historical_data WHERE Ticker = ? ORDER BY Date DESC LIMIT 1", (tk,)).fetchone()
                        prev_date = row[0] if row else None
                    except: prev_date = None

                    data = fetch_and_store(tk, conn)
                    if data is None: continue

                    curr_date = str(data['Date'].iloc[-1])
                    if prev_date and prev_date[:10] == curr_date[:10]:
                        pred_row = conn.execute("SELECT JSON_Blob FROM predictions WHERE Ticker = ?", (tk,)).fetchone()
                        if pred_row:
                            try:
                                rep = json.loads(pred_row[0])
                                lb.append({"Asset": tk, "Category": f"{asset_type}/{subcat}", "Price": f"₹{rep['Price']:,.2f}", "Signal": rep['Signal'], "Vol": f"{rep['Vol']*100:.2f}%", "Prob": f"{rep['Prob']:.1f}%", "Sharpe": f"{rep.get('Sharpe',0):.2f}", "MaxDD": f"{rep.get('MaxDD',0):.2f}%"})
                            except: pass
                            print(f"[{tk}] Unchanged ({curr_date[:10]}). Cached.")
                            continue

                    try:
                        ghost_xgb, ghost_lstm, err, h_r2, lstm_r2, feats, data = train_engine(data, tk, hyperparams)
                        
                        cols = [c for c in data.columns if c != 'Date']
                        data['Date'] = data['Date'].astype(str)
                        conn.execute("DELETE FROM historical_data WHERE Ticker = ?", (tk,))
                        data.to_sql("historical_data", conn, if_exists="append", index=False)
                        
                        sharpe, max_dd = precision_backtest(data, tk, conn)
                        prob, vol, scn, mcr, mc_paths = monte_carlo_sim(data, tk)
                        sentiment = get_sentiment(tk)
                        mc, pb, mom = get_factors(tk, data)
                        price = float(data['Close'].iloc[-1])
                        
                        data_sorted = data.sort_values('Date')
                        cagr = (((price + (data_sorted['Dividends'].sum() if 'Dividends' in data_sorted.columns else 0)) / float(data_sorted['Close'].iloc[0])) ** (1 / ((pd.to_datetime(data_sorted['Date'].iloc[-1]) - pd.to_datetime(data_sorted['Date'].iloc[0])).days / 365.25)) - 1) * 100 if len(data_sorted) > 200 else 0
                        down_std = data['Daily_Return'][data['Daily_Return'] < 0].std() * np.sqrt(252)
                        sortino = float(data['Daily_Return'].mean() * 252 / down_std) if down_std > 0 else 0
                        var_95 = float(np.percentile(data['Daily_Return'].dropna(), 5)) * 100
                        market_mode = "BULL 🐂" if price > float(data['SMA_50'].iloc[-1]) else "BEAR 🐻"
                        
                        pr = ((ghost_xgb[-1] - price) / price) * 100
                        sig = generate_signal(pr, sharpe, max_dd, market_mode, sentiment)

                        rep = {
                            "Ticker": tk, "Category": asset_type, "Subcategory": subcat,
                            "Price": price, "Signal": sig, "Ghost": ghost_xgb, "LSTM_Ghost": ghost_lstm,
                            "Scenarios": scn, "Macro": mcr, "MC_Paths": mc_paths, "Features": feats,
                            "Sentiment_Score": sentiment,
                            "Factors": {"Size_MCap": mc, "Value_PB": pb, "Momentum_6M": mom},
                            "Compat": h_r2, "LSTM_Compat": lstm_r2, "Error": err,
                            "Vol": vol, "Prob": prob, "Sharpe": sharpe, "MaxDD": max_dd,
                            "Market_Mode": market_mode,
                            "Technical_Indicators": {"RSI": float(data['RSI'].iloc[-1]), "MACD": float(data['MACD'].iloc[-1]), "BB_PB": float(data['BB_PB'].iloc[-1]), "ATR_14": float(data['ATR_14'].iloc[-1]), "Stoch_K": float(data['Stoch_K'].iloc[-1])},
                            "Investing_Tools": {"CAGR": cagr, "Sortino": sortino, "VaR_95": var_95, "Golden_Cross": "Golden Cross 🐂" if float(data['SMA_50'].iloc[-1]) > float(data['SMA_200'].iloc[-1]) else "Death Cross 🐻", "Dist_52W_High": ((price - float(data['High_52W'].iloc[-1])) / float(data['High_52W'].iloc[-1])) * 100 if float(data['High_52W'].iloc[-1]) > 0 else 0, "Dist_52W_Low": ((price - float(data['Low_52W'].iloc[-1])) / float(data['Low_52W'].iloc[-1])) * 100 if float(data['Low_52W'].iloc[-1]) > 0 else 0},
                            "Last_Updated": now.strftime('%Y-%m-%d %H:%M IST'),
                        }
                        
                        conn.execute("INSERT OR REPLACE INTO predictions (Ticker, Category, Subcategory, Price, Signal, Prob, Sharpe, MaxDD, Vol, Market_Mode, JSON_Blob) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                     (tk, asset_type, subcat, price, sig, prob, sharpe, max_dd, vol, market_mode, json.dumps(rep)))
                        conn.commit()
                        lb.append({"Asset": tk, "Category": f"{asset_type}/{subcat}", "Price": f"₹{price:,.2f}", "Signal": sig, "Vol": f"{vol*100:.2f}%", "Prob": f"{prob:.1f}%", "Sharpe": f"{sharpe:.2f}", "MaxDD": f"{max_dd:.2f}%"})
                    except Exception as ex: print(f"{BLINK_RED}[{tk}] Compute error: {ex}{RESET}")

        if lb:
            conn.execute("DELETE FROM leaderboard")
            pd.DataFrame(lb).to_sql("leaderboard", conn, if_exists="append", index=False)
            calculate_portfolio_weights(lb, conn)
            conn.commit()

        open(os.path.join(DATA_DIR, ".ready"), "w").close()
        wait = 3600 if market_live else 1800
        print(f"\n{BOLD_GREEN}[{now.strftime('%H:%M:%S')}] Cycle complete. Next check in {wait//60}m.{RESET}")
        time.sleep(wait)

if __name__ == "__main__":
    run_stock_market()
