# Copyright (c) 2026 mrQhere. All rights reserved.

import os
import json
import sqlite3
import pandas as pd
import xgboost as xgb
import optuna
from sklearn.metrics import mean_squared_error
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data_lake")
DB_PATH = os.path.join(DATA_DIR, "quant.db")
HYPERPARAMS_FILE = os.path.join(DATA_DIR, "hyperparams.json")

def load_data(ticker):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM historical_data WHERE Ticker = ?", conn, params=(ticker,))
    conn.close()
    return df

def objective(trial, X, y):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 500, 2000),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
        'max_depth': trial.suggest_int('max_depth', 3, 12),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'random_state': 42,
        'n_jobs': -1
    }
    
    train_size = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_val = y.iloc[:train_size], y.iloc[train_size:]
    
    model = xgb.XGBRegressor(**params)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_val)
    mse = mean_squared_error(y_val, preds)
    return mse

def optimize_ticker(ticker):
    print(f"Optimizing {ticker}...")
    df = load_data(ticker)
    if df.empty or len(df) < 200:
        return None
        
    features = ['Close', 'SMA_20', 'SMA_50', 'SMA_200', 'MACD', 'RSI', 'Volatility_20', 'BB_Width', 'BB_PB', 'ATR_14', 'Stoch_K', 'Stoch_D']
    # Check if features exist
    if not all(f in df.columns for f in features):
        return None

    X = df[features].iloc[:-1]
    y = df['Daily_Return'].shift(-1).dropna()
    X = X.loc[y.index]
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction='minimize')
    study.optimize(lambda trial: objective(trial, X, y), n_trials=10) # 10 trials for speed
    
    print(f"Best MSE for {ticker}: {study.best_value}")
    return study.best_params

def main():
    if not os.path.exists(DB_PATH):
        print("Database not found. Run the backend first.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        tickers = pd.read_sql("SELECT DISTINCT Ticker FROM historical_data", conn)['Ticker'].tolist()
    except Exception as e:
        print(f"Error reading tickers: {e}")
        return
    finally:
        conn.close()
    
    all_params = {}
    if os.path.exists(HYPERPARAMS_FILE):
        try:
            with open(HYPERPARAMS_FILE, 'r') as f:
                all_params = json.load(f)
        except: pass
            
    for ticker in tickers:
        best_p = optimize_ticker(ticker)
        if best_p:
            all_params[ticker] = best_p
            
    with open(HYPERPARAMS_FILE, 'w') as f:
        json.dump(all_params, f, indent=4)
        
    print("Optimization complete! Saved to hyperparams.json.")

if __name__ == "__main__":
    main()
