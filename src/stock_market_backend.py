# Copyright (c) 2026 mrQhere. All rights reserved.

import yfinance as yf
import pandas as pd
import numpy as np
import xgboost as xgb
from arch import arch_model
from sklearn.metrics import r2_score
import json, os, time, warnings, logging, sqlite3
from datetime import datetime, timedelta
import pytz
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout

import torch
import torch.nn as nn
import torch.optim as optim
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Hermes LLM Agent (optional — fails gracefully if ollama not installed/running)
try:
    from llm_agent import HermesAgent
    _hermes = HermesAgent()
except Exception as _hermes_err:
    _hermes = None
    print(f"[Hermes] Could not load agent: {_hermes_err}")

warnings.filterwarnings('ignore')

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE_DIR, "data_lake")
ASSET_FILE = os.path.join(BASE_DIR, "assets.json")
LOG_FILE  = os.path.join(BASE_DIR, "logs", "picks.log")
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
    # WAL mode: allows simultaneous readers while backend writes — eliminates lock errors
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
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

    # Walk-forward backtest validation — one row per ticker per cycle
    c.execute('''CREATE TABLE IF NOT EXISTS backtest_validation 
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                  Ticker TEXT, Date TEXT, Signal TEXT,
                  Price_At_Signal REAL, Price_Next_Day REAL,
                  Was_Correct INTEGER,
                  Walk30_Accuracy REAL)''')
    
    conn.commit()
    return conn

def fetch_and_store(ticker: str, conn: sqlite3.Connection) -> pd.DataFrame | None:
    print(f"\n{CYAN}[{ticker}] Syncing 5Y data from Yahoo Finance...{RESET}")
    try:
        raw = yf.Ticker(ticker).history(period="5y", auto_adjust=True, timeout=20)
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

        raw.dropna(subset=[c for c in raw.columns if c != 'Hist_Ghost_Price'], inplace=True)
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

def walk_forward_validate(ticker: str, current_price: float, current_signal: str, conn: sqlite3.Connection) -> float:
    """
    Every cycle: look up yesterday's recorded signal and compare its directional
    prediction to today's actual closing price.  Log the outcome, then return
    the rolling 30-day signal accuracy for this ticker.

    Returns
    -------
    float
        Accuracy in [0.0, 1.0].  Returns 0.5 (neutral) if fewer than 5
        validation rows exist (not enough history yet).
    """
    try:
        today_str = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d')

        # --- Update yesterday's pending row with the actual next-day price ---
        yesterday_row = conn.execute(
            """SELECT ID, Signal, Price_At_Signal FROM backtest_validation
               WHERE Ticker = ? AND Price_Next_Day IS NULL
               ORDER BY Date DESC LIMIT 1""",
            (ticker,)
        ).fetchone()

        if yesterday_row:
            row_id, prev_signal, prev_price = yesterday_row
            correct = 0
            if prev_price and prev_price > 0:
                direction_up = current_price > prev_price
                if ("BUY" in prev_signal and direction_up) or \
                   ("SELL" in prev_signal and not direction_up) or \
                   ("HOLD" in prev_signal):   # HOLD counts as neutral-correct
                    correct = 1
            conn.execute(
                """UPDATE backtest_validation
                   SET Price_Next_Day = ?, Was_Correct = ?
                   WHERE ID = ?""",
                (current_price, correct, row_id)
            )

        # --- Insert today's signal as a new pending row ---
        conn.execute(
            """INSERT INTO backtest_validation
               (Ticker, Date, Signal, Price_At_Signal, Price_Next_Day, Was_Correct, Walk30_Accuracy)
               VALUES (?, ?, ?, ?, NULL, NULL, NULL)""",
            (ticker, today_str, current_signal, current_price)
        )

        # --- Compute rolling 30-day accuracy ---
        rows = conn.execute(
            """SELECT Was_Correct FROM backtest_validation
               WHERE Ticker = ? AND Was_Correct IS NOT NULL
               ORDER BY Date DESC LIMIT 30""",
            (ticker,)
        ).fetchall()
        conn.commit()

        if len(rows) < 5:
            return 0.5   # not enough data — return neutral

        accuracy = sum(r[0] for r in rows) / len(rows)

        # Back-fill accuracy on today's row
        conn.execute(
            """UPDATE backtest_validation SET Walk30_Accuracy = ?
               WHERE Ticker = ? AND Date = ? AND Price_Next_Day IS NULL""",
            (accuracy, ticker, today_str)
        )
        conn.commit()
        return float(accuracy)

    except Exception as e:
        print(f"[{ticker}] walk_forward_validate error: {e}")
        return 0.5


def overfitting_score(holdout_r2: float, train_r2: float) -> float:
    """
    Return ratio of holdout R² to train R².
    A value < 0.4 strongly suggests the model memorised the training set.
    Returns 1.0 (healthy) if train_r2 is 0 or negative (edge case).
    """
    if train_r2 is None or train_r2 <= 0:
        return 1.0
    return float(holdout_r2 or 0) / float(train_r2)


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
    """Fetch news sentiment. yfinance .news does not accept a timeout kwarg in 1.5.2,
    so we wrap it in a short-lived ThreadPoolExecutor to bound the wait."""
    try:
        with ThreadPoolExecutor(max_workers=1) as _ex:
            future = _ex.submit(lambda: yf.Ticker(ticker).news)
            try:
                news = future.result(timeout=15)
            except FutTimeout:
                print(f"[{ticker}] .news timed out — skipping sentiment.")
                return 0.0
        analyzer = SentimentIntensityAnalyzer()
        scores = [analyzer.polarity_scores(n['title'])['compound'] for n in news if 'title' in n]
        return float(sum(scores)/len(scores)) if scores else 0.0
    except: return 0.0

def compute_piotroski(ticker_obj):
    """
    Piotroski F-Score (0-9). Field names verified against real yfinance 1.5.2 output
    for RELIANCE.NS, TCS.NS, and INFY.NS on 2026-07-28. All three tickers use:
      financials : 'Net Income', 'Gross Profit', 'Total Revenue'
      balance_sheet: 'Total Assets', 'Total Debt', 'Current Assets',
                     'Current Liabilities', 'Ordinary Shares Number'
      cashflow    : 'Operating Cash Flow'
    Each item lookup is individually guarded so one missing line item can't crash
    the score; the whole function catches top-level exceptions and returns None.
    """
    try:
        fin = ticker_obj.financials
        bs  = ticker_obj.balance_sheet
        cf  = ticker_obj.cashflow
        if fin.empty or bs.empty or cf.empty or fin.shape[1] < 2:
            return None
        cols = fin.columns[:2]  # most-recent year first

        def _get(frame, key, cols):
            return frame.loc[key, cols] if key in frame.index else None

        net_income    = _get(fin, 'Net Income', cols)
        op_cf         = _get(cf,  'Operating Cash Flow', cols)
        total_assets  = _get(bs,  'Total Assets', cols)
        total_debt    = _get(bs,  'Total Debt', cols)
        current_assets = _get(bs, 'Current Assets', cols)
        current_liab  = _get(bs,  'Current Liabilities', cols)
        shares        = _get(bs,  'Ordinary Shares Number', cols)
        revenue       = _get(fin, 'Total Revenue', cols)
        gross_profit  = _get(fin, 'Gross Profit', cols)

        score = 0
        try:
            if net_income is not None and net_income.iloc[0] > 0: score += 1
        except: pass
        try:
            if op_cf is not None and op_cf.iloc[0] > 0: score += 1
        except: pass
        try:
            if (net_income is not None and total_assets is not None and
                    len(net_income) > 1 and total_assets.iloc[1] > 0 and total_assets.iloc[0] > 0):
                if (net_income.iloc[0] / total_assets.iloc[0] >
                        net_income.iloc[1] / total_assets.iloc[1]):
                    score += 1
        except: pass
        try:
            if (op_cf is not None and net_income is not None and
                    op_cf.iloc[0] > net_income.iloc[0]):
                score += 1
        except: pass
        try:
            if (total_debt is not None and total_assets is not None and
                    len(total_debt) > 1 and total_assets.iloc[0] > 0 and total_assets.iloc[1] > 0):
                if (total_debt.iloc[0] / total_assets.iloc[0] <
                        total_debt.iloc[1] / total_assets.iloc[1]):
                    score += 1
        except: pass
        try:
            if (current_assets is not None and current_liab is not None and
                    len(current_assets) > 1 and current_liab.iloc[0] > 0 and current_liab.iloc[1] > 0):
                if (current_assets.iloc[0] / current_liab.iloc[0] >
                        current_assets.iloc[1] / current_liab.iloc[1]):
                    score += 1
        except: pass
        try:
            if shares is not None and len(shares) > 1:
                if shares.iloc[0] <= shares.iloc[1]: score += 1
        except: pass
        try:
            if (gross_profit is not None and revenue is not None and
                    len(gross_profit) > 1 and revenue.iloc[0] > 0 and revenue.iloc[1] > 0):
                if (gross_profit.iloc[0] / revenue.iloc[0] >
                        gross_profit.iloc[1] / revenue.iloc[1]):
                    score += 1
        except: pass
        try:
            if (revenue is not None and total_assets is not None and
                    len(revenue) > 1 and total_assets.iloc[0] > 0 and total_assets.iloc[1] > 0):
                if (revenue.iloc[0] / total_assets.iloc[0] >
                        revenue.iloc[1] / total_assets.iloc[1]):
                    score += 1
        except: pass

        return score
    except Exception:
        return None


def get_factors(ticker, df):
    try:
        t = yf.Ticker(ticker)
        with ThreadPoolExecutor(max_workers=1) as _ex:
            future = _ex.submit(lambda: t.info)
            try:
                info = future.result(timeout=15)
            except FutTimeout:
                print(f"[{ticker}] .info timed out — using defaults.")
                return 0, 0, 0.0, {}, None
        mc  = info.get('marketCap', 0)
        pb  = info.get('priceToBook', 0)
        mom = ((df['Close'].iloc[-1] - df['Close'].iloc[-126]) / df['Close'].iloc[-126] * 100) if len(df) > 126 else 0.0
        fundamentals = {
            "pe":                   info.get("trailingPE", 0),
            "forward_pe":           info.get("forwardPE", 0),
            "pb":                   pb,
            "roe":                  info.get("returnOnEquity", 0),
            "debt_to_equity":       info.get("debtToEquity", 0),
            "div_yield":            info.get("dividendYield", 0),
            "payout_ratio":         info.get("payoutRatio", 0),
            "revenue_growth":       info.get("revenueGrowth", 0),
            "earnings_growth":      info.get("earningsGrowth", 0),
            "insider_holding":      info.get("heldPercentInsiders", 0),
            "institutional_holding":info.get("heldPercentInstitutions", 0),
            "free_cashflow":        info.get("freeCashflow", 0),
        }
        piotroski = compute_piotroski(t)
        return mc, pb, mom, fundamentals, piotroski
    except: return 0, 0, 0.0, {}, None

def monte_carlo_sim(data: pd.DataFrame, ticker: str):
    rets = data['Daily_Return'].dropna() * 100
    try:
        v = arch_model(rets, vol='Garch', p=1, q=1).fit(disp='off').conditional_volatility.iloc[-1] / 100
    except:
        v = data['Volatility_20'].iloc[-1] if not pd.isna(data['Volatility_20'].iloc[-1]) else 0.02

    lp = float(data['Close'].iloc[-1])
    
    # 3a. Replace Gaussian shocks with historical block bootstrap
    hist_returns = data['Daily_Return'].dropna().values
    block_size = 5
    n_blocks = 252 // block_size + 1

    def bootstrap_path(hist_returns, n_blocks, block_size, start_price):
        prices = [start_price]
        for _ in range(n_blocks):
            start_idx = np.random.randint(0, len(hist_returns) - block_size)
            block = hist_returns[start_idx:start_idx + block_size]
            for r in block:
                prices.append(prices[-1] * (1 + r))
        return prices[:253]

    paths = np.array([bootstrap_path(hist_returns, n_blocks, block_size, lp) for _ in range(1000)]).T

    mc_paths = [paths[:30, i].tolist() for i in range(50)]
    
    # We will remove the old hardcoded macro scenarios here since UI will compute them
    macro = {}

    def sc(d): return {k: float(np.percentile(paths[d], p)) for k, p in [("Extreme_Good",95),("Good",75),("Most_Likely",50),("Bad",25),("Extreme_Bad",5)]}
    prob_up = float(np.mean(paths[30] > lp) * 100)
    return prob_up, v, {"7_Day": sc(7), "1_Month": sc(30), "1_Year": sc(251)}, macro, mc_paths

def generate_signal(pr: float, sharpe: float, max_dd: float, market_mode: str, sentiment: float) -> str:
    if pr > 5 and sentiment > 0: sig = "STRONG BUY 🟢"
    elif pr > 1.5: sig = "BUY ↗️"
    elif pr < -5 and sentiment < 0: sig = "STRONG SELL 🔴"
    elif pr < -1.5: sig = "SELL ↘️"
    else: sig = "HOLD ➖"

    # Risk gate: any one of these conditions caps a BUY-side signal at HOLD.
    # Previously only the BEAR+negative-sharpe combination was checked, so max_dd
    # was accepted as a parameter but never actually used — a BULL-mode ticker with
    # a catastrophic historical drawdown could still print STRONG BUY unchecked.
    risky = (
        ("BEAR" in market_mode and sharpe < 0) or
        (max_dd <= -20) or
        (sharpe < -0.5)
    )
    if risky and "BUY" in sig:
        sig = "HOLD ➖"
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

def _serve_stale(tk, asset_type, subcat, conn, lb, reason=""):
    """Re-serve the previous cycle's prediction for a failed ticker rather than
    dropping it from the leaderboard entirely. Marks the row Stale=True so the
    UI can display a warning badge. If no prior row exists, silently skips."""
    try:
        pred_row = conn.execute(
            "SELECT JSON_Blob FROM predictions WHERE Ticker = ?", (tk,)
        ).fetchone()
        if not pred_row:
            print(f"[{tk}] No stale data available — skipping. ({reason})")
            return
        rep = json.loads(pred_row[0])
        rep["Stale"] = True
        # Persist the stale flag back to the DB so the UI picks it up
        conn.execute(
            "UPDATE predictions SET JSON_Blob = ? WHERE Ticker = ?",
            (json.dumps(rep), tk)
        )
        conn.commit()
        lb.append({
            "Asset": tk,
            "Category": f"{asset_type}/{subcat}",
            "Price": f"₹{rep['Price']:,.2f} ⚠",
            "Signal": rep['Signal'],
            "Vol": f"{rep['Vol']*100:.2f}%",
            "Prob": f"{rep.get('Prob', 0):.1f}%",
            "Sharpe": f"{rep.get('Sharpe', 0):.2f}",
            "MaxDD": f"{rep.get('MaxDD', 0):.2f}%",
        })
        print(f"[{tk}] Serving stale data from previous cycle. ({reason})")
    except Exception as e:
        print(f"[{tk}] Could not serve stale data: {e}")

def _process_ticker(tk, asset_type, subcat, data, hyperparams, conn, now):
    """All per-ticker compute in one function so it can be submitted to the
    ThreadPoolExecutor with a hard timeout. Does not catch exceptions itself —
    the caller handles FutTimeout and general Exception."""
    ghost_xgb, ghost_lstm, err, h_r2, lstm_r2, feats, data = train_engine(data, tk, hyperparams)

    # Train R² estimate: use the first 60% of training data as a proxy
    try:
        feat_cols = ['Close', 'SMA_20', 'SMA_50', 'SMA_200', 'MACD', 'RSI',
                     'Volatility_20', 'BB_Width', 'BB_PB', 'ATR_14', 'Stoch_K', 'Stoch_D']
        _X = data[feat_cols].iloc[:-1]
        _y = data['Daily_Return'].shift(-1).dropna()
        _X = _X.loc[_y.index]
        _train_size = int(len(_X) * 0.6)
        if _train_size > 50:
            _mdl = xgb.XGBRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            _mdl.fit(_X.iloc[:_train_size], _y.iloc[:_train_size])
            _train_r2 = max(0, r2_score(_y.iloc[:_train_size], _mdl.predict(_X.iloc[:_train_size]))) * 100
        else:
            _train_r2 = 0.0
    except Exception:
        _train_r2 = 0.0

    data['Date'] = data['Date'].astype(str)
    conn.execute("DELETE FROM historical_data WHERE Ticker = ?", (tk,))
    data.to_sql("historical_data", conn, if_exists="append", index=False)

    sharpe, max_dd = precision_backtest(data, tk, conn)
    prob, vol, scn, mcr, mc_paths = monte_carlo_sim(data, tk)
    sentiment = get_sentiment(tk)
    mc, pb, mom, fundamentals, piotroski = get_factors(tk, data)
    price = float(data['Close'].iloc[-1])

    data_sorted = data.sort_values('Date')
    cagr = (((price + (data_sorted['Dividends'].sum() if 'Dividends' in data_sorted.columns else 0)) / float(data_sorted['Close'].iloc[0])) ** (1 / ((pd.to_datetime(data_sorted['Date'].iloc[-1]) - pd.to_datetime(data_sorted['Date'].iloc[0])).days / 365.25)) - 1) * 100 if len(data_sorted) > 200 else 0
    down_std = data['Daily_Return'][data['Daily_Return'] < 0].std() * np.sqrt(252)
    sortino = float(data['Daily_Return'].mean() * 252 / down_std) if down_std > 0 else 0
    var_95 = float(np.percentile(data['Daily_Return'].dropna(), 5)) * 100
    market_mode = "BULL 🐂" if price > float(data['SMA_50'].iloc[-1]) else "BEAR 🐻"

    pr = ((ghost_xgb[-1] - price) / price) * 100
    sig = generate_signal(pr, sharpe, max_dd, market_mode, sentiment)

    # ── Anti-overfitting guard ─────────────────────────────────────────────
    # 1. Holdout-to-train R² ratio: if the model memorised training data, demote.
    ov_score = overfitting_score(h_r2, _train_r2)
    overfit_flag = ov_score < 0.4 and _train_r2 > 5   # only flag if train_r2 is meaningful

    # 2. Walk-forward daily accuracy: record yesterday's outcome, get 30d rolling acc.
    walk_acc = walk_forward_validate(tk, price, sig, conn)

    # 3. If accuracy < 45% over last 30 signals AND we have enough data, cap at HOLD
    accuracy_flag = walk_acc < 0.45 and walk_acc != 0.5   # 0.5 = neutral (not enough data)

    if (overfit_flag or accuracy_flag) and "BUY" in sig:
        sig = "HOLD ➖"   # demote — system is not trustworthy enough on this ticker
        print(f"{YELLOW}[{tk}] Signal demoted to HOLD — overfit={overfit_flag} (score={ov_score:.2f}), accuracy_flag={accuracy_flag} ({walk_acc:.0%}).{RESET}")

    rep = {
        "Ticker": tk, "Category": asset_type, "Subcategory": subcat,
        "Price": price, "Signal": sig, "Ghost": ghost_xgb, "LSTM_Ghost": ghost_lstm,
        "Scenarios": scn, "Macro": mcr, "MC_Paths": mc_paths, "Features": feats,
        "Sentiment_Score": sentiment,
        "Factors": {"Size_MCap": mc, "Value_PB": pb, "Momentum_6M": mom},
        "Fundamentals": fundamentals,
        "Piotroski_Score": piotroski,
        "Compat": h_r2, "LSTM_Compat": lstm_r2, "Error": err,
        "Train_R2": _train_r2, "Overfit_Score": ov_score, "Overfit_Flag": overfit_flag,
        "Walk30_Accuracy": walk_acc, "Accuracy_Flag": accuracy_flag,
        "Vol": vol, "Prob": prob, "Sharpe": sharpe, "MaxDD": max_dd,
        "Market_Mode": market_mode,
        "Technical_Indicators": {"RSI": float(data['RSI'].iloc[-1]), "MACD": float(data['MACD'].iloc[-1]), "BB_PB": float(data['BB_PB'].iloc[-1]), "ATR_14": float(data['ATR_14'].iloc[-1]), "Stoch_K": float(data['Stoch_K'].iloc[-1])},
        "Investing_Tools": {"CAGR": cagr, "Sortino": sortino, "VaR_95": var_95, "Golden_Cross": "Golden Cross 🐂" if float(data['SMA_50'].iloc[-1]) > float(data['SMA_200'].iloc[-1]) else "Death Cross 🐻", "Dist_52W_High": ((price - float(data['High_52W'].iloc[-1])) / float(data['High_52W'].iloc[-1])) * 100 if float(data['High_52W'].iloc[-1]) > 0 else 0, "Dist_52W_Low": ((price - float(data['Low_52W'].iloc[-1])) / float(data['Low_52W'].iloc[-1])) * 100 if float(data['Low_52W'].iloc[-1]) > 0 else 0},
        "Last_Updated": now.strftime('%Y-%m-%d %H:%M IST'),
        "Hermes_Analysis": None,   # filled below if Hermes is available
        "Stale": False,
    }

    # ── Hermes LLM analysis (non-blocking, 30s timeout) ───────────────────
    if _hermes and _hermes.is_available:
        try:
            rep["Hermes_Analysis"] = _hermes.analyze(rep)
        except Exception as _he:
            print(f"[{tk}] Hermes analyze error: {_he}")

    lb_entry = {"Asset": tk, "Category": f"{asset_type}/{subcat}", "Price": f"₹{price:,.2f}", "Signal": sig, "Vol": f"{vol*100:.2f}%", "Prob": f"{prob:.1f}%", "Sharpe": f"{sharpe:.2f}", "MaxDD": f"{max_dd:.2f}%"}
    return rep, lb_entry


# Shared executor — max_workers=3 is deliberate: network-bound fetches benefit from
# concurrency even on a 2-core CPU, but LSTM/XGBoost training will contend above ~4.
_executor = ThreadPoolExecutor(max_workers=3)


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
                    if data is None or data.empty:
                        # Fetch failed — try stale fallback
                        _serve_stale(tk, asset_type, subcat, conn, lb, reason="fetch failed")
                        continue

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

                    # Submit compute work with a hard 120s timeout.
                    future = _executor.submit(_process_ticker, tk, asset_type, subcat, data, hyperparams, conn, now)
                    try:
                        rep, lb_entry = future.result(timeout=120)
                        conn.execute(
                            "INSERT OR REPLACE INTO predictions (Ticker, Category, Subcategory, Price, Signal, Prob, Sharpe, MaxDD, Vol, Market_Mode, JSON_Blob) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (tk, rep['Category'], rep['Subcategory'], rep['Price'], rep['Signal'],
                             rep['Prob'], rep['Sharpe'], rep['MaxDD'], rep['Vol'],
                             rep['Market_Mode'], json.dumps(rep))
                        )
                        conn.commit()
                        lb.append(lb_entry)
                    except FutTimeout:
                        print(f"{YELLOW}[{tk}] Timed out after 120s — serving stale data.{RESET}")
                        _serve_stale(tk, asset_type, subcat, conn, lb, reason="timeout")
                    except Exception as ex:
                        print(f"{BLINK_RED}[{tk}] Compute error: {ex}{RESET}")
                        _serve_stale(tk, asset_type, subcat, conn, lb, reason=str(ex))

        if lb:
            conn.execute("DELETE FROM leaderboard")
            pd.DataFrame(lb).to_sql("leaderboard", conn, if_exists="append", index=False)
            calculate_portfolio_weights(lb, conn)
            conn.commit()

        # ── Hermes daily review & asset suggestions ───────────────────────
        if _hermes and _hermes.is_available and lb:
            try:
                # Build price-change dict for this cycle vs previous cycle
                price_changes = {}
                for item in lb:
                    tk_name = item.get("Asset", "")
                    try:
                        # Get the two most recent close prices from DB
                        rows = conn.execute(
                            "SELECT Close FROM historical_data WHERE Ticker = ? ORDER BY Date DESC LIMIT 2",
                            (tk_name,)
                        ).fetchall()
                        if len(rows) >= 2:
                            price_changes[tk_name] = (rows[0][0] - rows[1][0]) / rows[1][0] * 100
                    except Exception:
                        pass

                review_text = _hermes.daily_review(lb, price_changes)
                print(f"\n{CYAN}[Hermes Daily Review]\n{review_text}{RESET}")

                suggestions = _hermes.suggest_asset_changes(lb)
                print(f"\n{CYAN}[Hermes Asset Suggestions]\n{suggestions}{RESET}")

                # Save review to a log file
                review_path = os.path.join(LOG_DIR, "hermes_review.log")
                with open(review_path, "a") as rf:
                    rf.write(f"\n[{now.strftime('%Y-%m-%d %H:%M')}]\nREVIEW: {review_text}\nSUGGESTIONS: {suggestions}\n")
            except Exception as _rev_err:
                print(f"{YELLOW}[Hermes] Daily review error: {_rev_err}{RESET}")

        open(os.path.join(DATA_DIR, ".ready"), "w").close()
        wait = 3600 if market_live else 1800
        print(f"\n{BOLD_GREEN}[{now.strftime('%H:%M:%S')}] Cycle complete. Next check in {wait//60}m.{RESET}")
        time.sleep(wait)

if __name__ == "__main__":
    run_stock_market()
