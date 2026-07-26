import sys
import os
import pytest
import pandas as pd
import numpy as np

# Adjust path to import from parent dir
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from stock_market_backend import generate_signal, precision_backtest

def test_generate_signal():
    # Bull mode, positive sharpe, high pr -> STRONG BUY
    assert "STRONG BUY" in generate_signal(pr=6.0, sharpe=1.2, max_dd=-5.0, market_mode="BULL 🐂")
    
    # Bear mode, positive sharpe, high pr -> STRONG BUY
    assert "STRONG BUY" in generate_signal(pr=6.0, sharpe=1.2, max_dd=-5.0, market_mode="BEAR 🐻")

    # Bear mode, negative sharpe, high pr -> cap at HOLD
    assert "HOLD" in generate_signal(pr=6.0, sharpe=-0.24, max_dd=-16.71, market_mode="BEAR 🐻")
    
    # Bear mode, negative sharpe, negative pr -> SELL
    assert "SELL" in generate_signal(pr=-2.0, sharpe=-0.5, max_dd=-20.0, market_mode="BEAR 🐻")

def test_technical_indicators_and_risk():
    # Create a synthetic equity curve
    dates = pd.date_range("2020-01-01", periods=200, freq="D")
    # Linear price increase with some drop in the middle
    prices = np.linspace(100, 200, 200)
    prices[100:120] = prices[100:120] * 0.8  # Introduce a 20% drawdown
    
    df = pd.DataFrame({"Date": dates, "Close": prices, "High": prices * 1.05, "Low": prices * 0.95})
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    # Dummy Hist_Ghost_Price so it uses AI logic
    df['Hist_Ghost_Price'] = df['Close'] * 1.01 
    df['Daily_Return'] = df['Close'].pct_change()
    df.dropna(inplace=True)
    
    # We will test precision_backtest logic (Sharpe & max DD)
    sharpe, max_dd = precision_backtest(df, "/tmp")
    
    assert isinstance(sharpe, float)
    assert isinstance(max_dd, float)
    assert max_dd < 0  # Should catch the drawdown
    assert sharpe > 0  # Overall positive return
