import sys
import os
import sqlite3
import pytest
import pandas as pd
import numpy as np

# Adjust path to import from parent dir
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from stock_market_backend import generate_signal, precision_backtest

def test_generate_signal():
    # Bull mode, positive sharpe, high pr, positive sentiment -> STRONG BUY
    assert "STRONG BUY" in generate_signal(pr=6.0, sharpe=1.2, max_dd=-5.0, market_mode="BULL 🐂", sentiment=0.3)

    # Bear mode, positive sharpe, high pr, positive sentiment -> STRONG BUY allowed
    assert "STRONG BUY" in generate_signal(pr=6.0, sharpe=1.2, max_dd=-5.0, market_mode="BEAR 🐻", sentiment=0.3)

    # Bear mode, negative sharpe, high pr -> capped at HOLD regardless of sentiment
    assert "HOLD" in generate_signal(pr=6.0, sharpe=-0.24, max_dd=-16.71, market_mode="BEAR 🐻", sentiment=0.3)

    # Bear mode, negative sharpe, negative pr -> SELL
    assert "SELL" in generate_signal(pr=-2.0, sharpe=-0.5, max_dd=-20.0, market_mode="BEAR 🐻", sentiment=-0.3)

    # BULL mode, catastrophic drawdown, high pr -> should NOT be an uncapped STRONG BUY
    # (this is the max_dd blind spot: currently generate_signal ignores max_dd entirely
    # outside the BEAR+sharpe<0 branch, so this test documents the gap and will fail
    # until max_dd is actually used as a cap condition)
    assert "STRONG BUY" not in generate_signal(pr=6.0, sharpe=0.1, max_dd=-35.0, market_mode="BULL 🐂", sentiment=0.3)

def test_technical_indicators_and_risk():
    # Create a synthetic equity curve
    dates = pd.date_range("2020-01-01", periods=200, freq="D")
    # Linear price increase with some drop in the middle
    prices = np.linspace(100, 200, 200)
    prices[100:120] = prices[100:120] * 0.8  # Introduce a 20% drawdown
    
    df = pd.DataFrame({"Date": dates, "Close": prices, "High": prices * 1.05, "Low": prices * 0.95})
    df['Ticker'] = "TEST.NS"  # precision_backtest writes to a 'backtests' table keyed on Ticker
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    # Dummy Hist_Ghost_Price so it uses AI logic
    df['Hist_Ghost_Price'] = df['Close'] * 1.01
    df['Daily_Return'] = df['Close'].pct_change()
    df.dropna(inplace=True)

    # precision_backtest(data, ticker, conn) needs a real sqlite connection with the
    # 'backtests' table present, since it deletes/inserts rows as a side effect.
    conn = sqlite3.connect(":memory:")
    conn.execute('''CREATE TABLE backtests (Ticker TEXT, Date TEXT, Hold_Equity REAL, Strategy_Equity REAL)''')

    sharpe, max_dd = precision_backtest(df, "TEST.NS", conn)
    conn.close()

    assert isinstance(sharpe, float)
    assert isinstance(max_dd, float)
    assert max_dd < 0  # Should catch the drawdown
    assert sharpe > 0  # Overall positive return
