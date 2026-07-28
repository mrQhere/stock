# Stock Market Predictor — Complete User Guide
*Copyright (c) 2026 mrQhere — MIT License*

> [!CAUTION]
> **NOT FINANCIAL ADVICE.** Every model in this system is a mathematical approximation of historical market behaviour. It cannot predict the future. Black swan events — pandemics, sudden regulatory crackdowns, geopolitical shocks — will break these models. Use this strictly as a research and learning terminal. Never deploy real capital based solely on its outputs.

---

## Table of Contents

### Part 1 — Beginner Setup (Start Here)
1. [What This Tool Does](#1-what-this-tool-does)
2. [System Requirements](#2-system-requirements)
3. [First-Time Installation (Copy-Paste)](#3-first-time-installation-copy-paste)
4. [Setting Your Password and API Key](#4-setting-your-password-and-api-key)
5. [Starting the System](#5-starting-the-system)
6. [Choosing a Mode](#6-choosing-a-mode)
7. [Reading the Dashboard — Investor Mode](#7-reading-the-dashboard--investor-mode)
8. [Reading the Dashboard — Advanced Mode](#8-reading-the-dashboard--advanced-mode)

### Part 2 — System Architecture
9. [The Three-Process Architecture](#9-the-three-process-architecture)
10. [The Data Pipeline](#10-the-data-pipeline)
11. [SQLite as the State Manager](#11-sqlite-as-the-state-manager)
12. [Fault Tolerance and Stale Data](#12-fault-tolerance-and-stale-data)

### Part 3 — Mathematical Theorems (The Core)
13. [Technical Indicators: Full Derivations](#13-technical-indicators-full-derivations)
14. [XGBoost: Gradient Boosting Theory](#14-xgboost-gradient-boosting-theory)
15. [LSTM: Sequence Modelling Theory](#15-lstm-sequence-modelling-theory)
16. [Monte Carlo Block Bootstrap](#16-monte-carlo-block-bootstrap)
17. [GARCH Volatility Modelling](#17-garch-volatility-modelling)
18. [Risk Metrics: Sharpe, Sortino, VaR, Max Drawdown](#18-risk-metrics-sharpe-sortino-var-max-drawdown)
19. [Piotroski F-Score: Fundamental Analysis](#19-piotroski-f-score-fundamental-analysis)
20. [Signal Generation and Risk Gates](#20-signal-generation-and-risk-gates)
21. [SIP Calculator: Time Value of Money](#21-sip-calculator-time-value-of-money)
22. [Sentiment Analysis: VADER](#22-sentiment-analysis-vader)

### Part 4 — Advanced Operations
23. [Customising assets.json](#23-customising-assetsjson)
24. [Bayesian Hyperparameter Tuning (Optuna)](#24-bayesian-hyperparameter-tuning-optuna)
25. [REST API Reference](#25-rest-api-reference)
26. [Troubleshooting Guide](#26-troubleshooting-guide)

---

# PART 1 — BEGINNER SETUP

## 1. What This Tool Does

This is a **locally-hosted quantitative research terminal**. It downloads 5 years of market data for every asset you configure, trains two AI models (XGBoost and LSTM), runs a Monte Carlo risk simulation, computes fundamental scores, and displays everything in a web dashboard — all on your own machine, with no subscriptions and no data leaving your computer.

**Investor Mode** gives you:
- Price snapshot: 1Y return, 5Y CAGR, dividend yield
- Fundamentals table: P/E, P/B, ROE, debt ratios, insider holdings
- Piotroski F-Score: a 9-point financial health check
- SIP/Goal Calculator: how long to reach a target corpus

**Advanced Mode adds:**
- AI buy/sell signal from the ensemble of both models
- 7-day price projection ("Ghost Path")
- Monte Carlo Capital Deployment Scenarios
- Black Swan scenario overlays with real historical crash data
- Sharpe Ratio, Sortino Ratio, Max Drawdown, GARCH Volatility
- Risk Parity portfolio weights

---

## 2. System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | Linux, macOS, Windows (WSL2) | Ubuntu 22.04 LTS |
| Python | 3.12 | 3.12 |
| RAM | 4 GB | 8 GB |
| Storage | 3 GB free | 10 GB free |
| Internet | Required for data fetch | Broadband |
| GPU | Not needed | Not needed (CPU-only PyTorch) |

---

## 3. First-Time Installation (Copy-Paste)

Open a terminal and run these commands **one block at a time**:

**Step 1 — Clone the repository**
```bash
git clone https://github.com/mrQhere/stock.git
cd stock
```

**Step 2 — Create your password file**
```bash
mkdir -p .streamlit
cat > .streamlit/secrets.toml << 'EOF'
APP_PASSWORD = "change_this_to_your_password"
EOF
```

**Step 3 — Set your API key** (required to use the REST API)
```bash
# Add this to your ~/.bashrc or ~/.zshrc so it persists across sessions
echo 'export QUANT_API_KEY="change_this_to_your_api_key"' >> ~/.bashrc
source ~/.bashrc
```

**Step 4 — Make the boot script executable and run it**
```bash
chmod +x stock_market_boot.sh
./stock_market_boot.sh
```

The script will:
1. Detect your OS and install missing system dependencies automatically
2. Create a Python virtual environment at `jarvis_env/`
3. Install PyTorch (CPU-only, ~500 MB — not the 3 GB CUDA version)
4. Install all other pinned dependencies
5. Launch the backend data engine in the background
6. Show a progress bar while all tickers compile
7. Ask you to select Investor or Advanced mode
8. Open the Streamlit dashboard in your browser

> **First run takes 5–20 minutes** depending on internet speed and number of tickers. After the first run, subsequent boots are much faster because data is cached in `data_lake/quant.db`.

---

## 4. Setting Your Password and API Key

### UI Password
The dashboard requires a password every time you open it.

Edit `.streamlit/secrets.toml`:
```toml
APP_PASSWORD = "my_strong_password_123"
```

> This file is in `.gitignore` — it will never be accidentally committed to GitHub.

### API Key
All REST API endpoints except the health check require an `X-API-Key` header. If you skip this, all API calls return `HTTP 401`.

```bash
export QUANT_API_KEY="my_secure_api_key_abc123"
```

To make it permanent:
```bash
echo 'export QUANT_API_KEY="my_secure_api_key_abc123"' >> ~/.bashrc
source ~/.bashrc
```

---

## 5. Starting the System

**Normal start (after first run):**
```bash
cd stock
./stock_market_boot.sh
```

**Manual start (for debugging):**
```bash
cd stock
source jarvis_env/bin/activate

# Terminal 1: backend engine
python stock_market_backend.py

# Terminal 2: REST API
uvicorn api_server:app --host 0.0.0.0 --port 8000

# Terminal 3: dashboard
streamlit run stock_market_ui.py
```

**Check if backend is running:**
```bash
ps aux | grep stock_market_backend.py
tail -f logs/backend.log
```

**Stop everything:**
```bash
pkill -f stock_market_backend.py
pkill -f stock_market_ui.py
pkill -f uvicorn
```

---

## 6. Choosing a Mode

When the boot script finishes compiling data, it asks:

```
Select mode:
  1) Simple Long-Term Investor   (fundamentals, Piotroski, SIP calculator)
  2) Advanced Trader             (all panels + signal, Monte Carlo, backtest)
> 
```

- Press `1` + Enter for **Investor Mode** (recommended for beginners)
- Press `2` + Enter for **Advanced Mode**

You can flip between modes at any time using the **⚙️ Advanced Mode** toggle in the dashboard sidebar — no restart needed.

---

## 7. Reading the Dashboard — Investor Mode

When you open the dashboard, select a stock from the **"Select Asset to Analyze"** dropdown in the left sidebar.

**Price Snapshot (top row)**
| Metric | What it means |
|---|---|
| Current Price | Last closing price from Yahoo Finance |
| 1Y Return | % change from 252 trading days ago to today |
| 5Y CAGR | Compound Annual Growth Rate over 5 years including dividends |
| Dividend Yield | Annual dividend as % of current price |

**Company Snapshot**
| Metric | What it means |
|---|---|
| Market Cap | Total company value = shares outstanding × price |
| Price/Book | Share price ÷ book value per share |
| 6M Momentum | % price change over last 126 trading days |
| News Sentiment | VADER NLP score on recent headlines: −1 bearish → +1 bullish |

**Fundamentals Table** — 12 rows with plain-English explanations inline.

**Piotroski F-Score** — A number from 0 to 9. Green ≥ 7, Yellow 4–6, Red ≤ 3.

**SIP & Goal Calculator** — Enter a monthly amount, horizon in years, and target corpus. The calculator uses the ticker's own 5-year CAGR, not a generic 12% assumption.

---

## 8. Reading the Dashboard — Advanced Mode

*All investor panels remain visible. Additional panels appear below.*

**AI Signal Box** — One of: `STRONG BUY 🟢`, `BUY ↗️`, `HOLD ➖`, `SELL ↘️`, `STRONG SELL 🔴`. This is produced by the `generate_signal()` function described in Section 20.

**Quant Metrics Row**
| Metric | Good range | Bad range |
|---|---|---|
| Sharpe Ratio | > 1.0 | < 0 |
| Max Drawdown | > −15% | < −30% |
| Win Probability | > 60% | < 40% |
| GARCH Volatility | Contextual | > 4%/day = high risk |

**Capital Deployment Scenarios** — Monte Carlo percentile table. Read as: "If I invest today, there is a 5% chance the price will be at or below the Extreme Bad value in 1 year."

**Black Swan Toggles** (sidebar) — Toggle on to re-run the Monte Carlo using real crash return sequences from that period. Both the chart overlay *and* the percentile table update.

---

# PART 2 — SYSTEM ARCHITECTURE

## 9. The Three-Process Architecture

The system runs as three independent OS processes:

```
┌─────────────────────────────────────────────────────────┐
│  stock_market_boot.sh                                    │
│  (orchestrator — launches and monitors the other three) │
└────────────────┬────────────────────────────────────────┘
                 │ spawns
     ┌───────────┼───────────┐
     ▼           ▼           ▼
[backend.py]  [api_server] [streamlit UI]
  writes to     reads from   reads from
  quant.db      quant.db     quant.db
```

**Why three separate processes?**
- The backend runs infinite loops with heavy ML training. If it were in the same process as the UI, a crash or OOM in the backend would take down the dashboard.
- SQLite is used as the communication bus — all three processes share the same file. The backend writes, the others read. This avoids shared memory and IPC complexity.
- The FastAPI server is optional: if you only use the Streamlit UI, you can ignore it entirely.

---

## 10. The Data Pipeline

For each ticker, the backend executes this pipeline every cycle:

```
Yahoo Finance (yfinance)
        │
        ▼ 5 years OHLCV daily data
fetch_and_store()
        │ computes 12 technical indicators
        ▼
historical_data table (SQLite)
        │
        ├──► train_engine()          ─► XGBoost model + 7-day ghost path
        │         └──► train_lstm()  ─► LSTM model + 7-day ghost path
        │
        ├──► precision_backtest()    ─► Sharpe, Max Drawdown
        ├──► monte_carlo_sim()       ─► 1000-path bootstrap simulation
        ├──► get_sentiment()         ─► VADER NLP score
        ├──► get_factors()           ─► Fundamentals + Piotroski score
        │
        ▼
generate_signal()  ─► final signal with risk gates
        │
        ▼
predictions table (JSON blob per ticker)
        │
        ▼
Streamlit UI reads on next page load
```

**Timeout safety:** Every ticker is submitted to a `ThreadPoolExecutor` with a 120-second hard timeout. If training takes longer (e.g., slow network + large dataset), the ticker is skipped for this cycle and the previous result is re-served with a ⚠ stale badge.

---

## 11. SQLite as the State Manager

All persistent state lives in `data_lake/quant.db`. Key tables:

| Table | Contents | Written by | Read by |
|---|---|---|---|
| `historical_data` | OHLCV + 12 indicators, 1 row per date per ticker | backend | UI (chart) |
| `predictions` | One row per ticker; JSON blob contains MC paths, ghost arrays | backend | UI, API |
| `leaderboard` | Summary row per ticker for master table | backend | UI |
| `backtests` | Equity curve for hold vs. strategy | backend | UI (chart) |
| `portfolio_weights` | Risk parity weights | backend | UI |
| `portfolio_trades` | User-entered paper trades | UI | UI |

**WAL mode tip:** If you see `sqlite3.OperationalError: database is locked`, add this to `init_db()`:
```python
conn.execute('PRAGMA journal_mode=WAL')
```
WAL (Write-Ahead Logging) allows simultaneous readers while the backend writes, eliminating lock contention entirely.

---

## 12. Fault Tolerance and Stale Data

The `_serve_stale()` function is called whenever a ticker fails (network timeout, compute error, or the 120s execution limit). It:

1. Reads the last successful `JSON_Blob` for that ticker from `predictions`
2. Sets `"Stale": True` in the dict
3. Writes it back to the DB
4. Appends the ticker to the leaderboard with a `⚠` suffix on the price

The UI checks `rep.get("Stale")` and shows a yellow warning banner at the top of the analysis panel if the data is stale.

**No ticker ever disappears silently.** The worst case is showing yesterday's numbers with a warning badge.

---

*[Continued in Part 3: Mathematical Theorems]*

---

# PART 3 — MATHEMATICAL THEOREMS

## 13. Technical Indicators: Full Derivations

All indicators are computed from raw OHLCV data inside `fetch_and_store()`. No external TA library — every formula is implemented explicitly.

### 13.1 Simple Moving Average (SMA)

$$\text{SMA}_n(t) = \frac{1}{n} \sum_{i=0}^{n-1} \text{Close}_{t-i}$$

The SMA smooths price noise. We compute SMA-20, SMA-50, and SMA-200. A "Golden Cross" is when SMA-50 crosses above SMA-200 — a historically bullish regime signal. A "Death Cross" is the reverse.

```python
raw['SMA_20'] = raw['Close'].rolling(20).mean()
```

### 13.2 Exponential Moving Average (EMA)

$$\text{EMA}_t = \text{Close}_t \cdot \alpha + \text{EMA}_{t-1} \cdot (1 - \alpha), \quad \alpha = \frac{2}{n+1}$$

EMA weights recent prices more heavily than SMA. We compute EMA-12 and EMA-26.

### 13.3 MACD (Moving Average Convergence Divergence)

$$\text{MACD}_t = \text{EMA}_{12}(t) - \text{EMA}_{26}(t)$$

MACD measures momentum. When MACD crosses zero from below, it signals a potential upward momentum shift. It is one of the 12 features fed into both the XGBoost and LSTM models.

### 13.4 RSI (Relative Strength Index)

$$\text{RSI} = 100 - \frac{100}{1 + RS}, \quad RS = \frac{\overline{\text{Gain}_{14}}}{\overline{\text{Loss}_{14}}}$$

Where the gain/loss averages are computed over a 14-day rolling window. RSI oscillates between 0 and 100. Above 70 signals potential overbought conditions; below 30 signals potential oversold.

```python
delta = raw['Close'].diff()
gain  = delta.clip(lower=0).rolling(14).mean()
loss  = (-delta.clip(upper=0)).rolling(14).mean()
rs    = gain / loss.replace(0, np.nan)
raw['RSI'] = 100 - (100 / (1 + rs))
```

### 13.5 Bollinger Bands

$$\text{Upper} = \text{SMA}_{20} + 2\sigma_{20}, \quad \text{Lower} = \text{SMA}_{20} - 2\sigma_{20}$$

Where $\sigma_{20}$ is the 20-day rolling standard deviation of Close.

**BB Width** = $(\text{Upper} - \text{Lower}) / \text{SMA}_{20}$ — measures volatility expansion/contraction.

**BB %B (BB_PB)** = $(\text{Close} - \text{Lower}) / (\text{Upper} - \text{Lower})$ — where the price sits within the band. Values near 1 = near upper band; values near 0 = near lower band.

### 13.6 ATR (Average True Range)

$$\text{TR}_t = \max(\text{High}_t - \text{Low}_t,\ |\text{High}_t - \text{Close}_{t-1}|,\ |\text{Low}_t - \text{Close}_{t-1}|)$$

$$\text{ATR}_{14} = \frac{1}{14} \sum_{i=0}^{13} \text{TR}_{t-i}$$

ATR measures volatility in price terms (rupees/dollars), not percentage. A high ATR means large day-to-day price swings — higher risk per trade.

### 13.7 Stochastic Oscillator

$$K_t = 100 \cdot \frac{\text{Close}_t - \text{Low}_{14}}{\text{High}_{14} - \text{Low}_{14}}$$

$$D_t = \text{SMA}_3(K)$$

Where $\text{Low}_{14}$ and $\text{High}_{14}$ are the 14-day rolling minimum and maximum. Stoch-K oscillates 0–100. Above 80 = overbought zone; below 20 = oversold zone.

---

## 14. XGBoost: Gradient Boosting Theory

### 14.1 What XGBoost is solving

We frame price forecasting as a regression problem. The target $y_t$ is the **next day's return**:

$$y_t = \frac{\text{Close}_{t+1} - \text{Close}_t}{\text{Close}_t}$$

The 12 features $\mathbf{x}_t$ are: `Close, SMA_20, SMA_50, SMA_200, MACD, RSI, Volatility_20, BB_Width, BB_PB, ATR_14, Stoch_K, Stoch_D`.

### 14.2 Gradient Boosting: the ensemble mechanism

XGBoost builds an additive ensemble of $T$ shallow decision trees $f_1, f_2, \ldots, f_T$:

$$\hat{y}_t = \sum_{k=1}^{T} f_k(\mathbf{x}_t)$$

Each tree $f_k$ is trained to predict the **residual error** of the previous ensemble. Formally, at step $k$ we minimise:

$$\mathcal{L}^{(k)} = \sum_{i} l\left(y_i,\ \hat{y}_i^{(k-1)} + f_k(\mathbf{x}_i)\right) + \Omega(f_k)$$

Where $l$ is squared error for regression and $\Omega(f_k) = \gamma T_k + \frac{1}{2}\lambda \|w\|^2$ is a regularisation term penalising tree complexity ($T_k$ = number of leaves, $w$ = leaf weights).

### 14.3 Second-order Taylor approximation

XGBoost speeds up the optimisation by approximating the loss with its second-order Taylor expansion:

$$\mathcal{L}^{(k)} \approx \sum_i \left[ g_i f_k(\mathbf{x}_i) + \frac{1}{2} h_i f_k(\mathbf{x}_i)^2 \right] + \Omega(f_k)$$

Where $g_i = \partial_{\hat{y}} l(y_i, \hat{y}_i)$ (first derivative) and $h_i = \partial^2_{\hat{y}} l(y_i, \hat{y}_i)$ (second derivative, the Hessian). For squared error: $g_i = \hat{y}_i - y_i$, $h_i = 1$.

This closed-form gradient allows XGBoost to find optimal leaf weights analytically, making it far faster than naive boosting.

### 14.4 Regularisation in our codebase

Key hyperparameters tuned by Optuna:
- `subsample` — fraction of rows sampled per tree (< 1.0 prevents overfitting to market noise)
- `colsample_bytree` — fraction of features sampled per tree (prevents the model from depending entirely on one indicator)
- `max_depth` — maximum tree depth (deeper = more complex patterns, higher overfit risk)
- `learning_rate` (η) — shrinks each tree's contribution; lower = more trees needed, but better generalisation

### 14.5 Holdout integrity

The backend deliberately reserves the most recent 20% of data (minimum 60 days) as a holdout set. The XGBoost model is **never trained on this data**. The `Compat` (compatibility) metric shown in the UI is the $R^2$ score on this unseen holdout:

$$R^2 = 1 - \frac{\sum_i (y_i - \hat{y}_i)^2}{\sum_i (y_i - \bar{y})^2}$$

An $R^2$ near 0 means the model predicts no better than the mean. An $R^2$ of 0.15–0.25 is considered strong for daily return prediction; markets are nearly random at this timescale.

---

## 15. LSTM: Sequence Modelling Theory

### 15.1 Why a recurrent architecture

XGBoost treats each day as an independent observation. The LSTM (Long Short-Term Memory) is given a **rolling 5-day window** of all 12 features, preserving the temporal ordering. This allows the model to learn sequential patterns — e.g., "three consecutive days of narrowing Bollinger Bands followed by a spike in ATR tends to precede a breakout."

### 15.2 The LSTM cell equations

At each time step $t$, the LSTM computes:

$$f_t = \sigma(W_f \cdot [h_{t-1}, x_t] + b_f) \quad \text{(forget gate)}$$
$$i_t = \sigma(W_i \cdot [h_{t-1}, x_t] + b_i) \quad \text{(input gate)}$$
$$\tilde{C}_t = \tanh(W_C \cdot [h_{t-1}, x_t] + b_C) \quad \text{(candidate cell state)}$$
$$C_t = f_t \odot C_{t-1} + i_t \odot \tilde{C}_t \quad \text{(cell state update)}$$
$$o_t = \sigma(W_o \cdot [h_{t-1}, x_t] + b_o) \quad \text{(output gate)}$$
$$h_t = o_t \odot \tanh(C_t) \quad \text{(hidden state)}$$

Where $\sigma$ is the sigmoid function, $\odot$ is element-wise multiplication. The **forget gate** $f_t$ controls how much of the previous cell state to retain. This is what gives LSTM its ability to "remember" patterns from many steps ago — something a vanilla RNN cannot do due to the vanishing gradient problem.

### 15.3 Z-score normalisation

The LSTM never sees raw prices. Features are normalised per sequence:

$$X_{\text{scaled}} = \frac{X - \mu_X}{\sigma_X}$$

And targets (next-day returns) are normalised:

$$y_{\text{scaled}} = \frac{y - \mu_y}{\sigma_y}$$

This makes the model universally applicable across all tickers regardless of absolute price level, immune to stock splits, and prevents gradient explosion during backpropagation.

### 15.4 Autoregressive 7-day projection

After training, the LSTM generates the 7-day ghost path autoregressively:
1. Feed the last 5-day window to the model → predict return $r_1$
2. Compute new price: $P_1 = P_0 \cdot (1 + r_1)$, clip $r_1$ to $[\!-10\%, +10\%\!]$
3. Update the input sequence: drop the oldest day, append the new predicted day
4. Repeat 7 times

The clipping at ±10% is intentional — unconstrained autoregression diverges exponentially for volatile assets. The clip reflects a reasonable single-day move limit for most equities.

---

## 16. Monte Carlo Block Bootstrap

### 16.1 The problem with Gaussian Monte Carlo

The classic Monte Carlo simulation draws shocks from $\mathcal{N}(\mu, \sigma^2)$. This is mathematically clean but empirically wrong for financial returns because:

- **Fat tails:** Market crashes happen far more frequently than a Gaussian predicts. A −10% single-day move is a 10-sigma event under Gaussian assumptions, yet it occurs in reality.
- **Volatility clustering:** High-volatility periods cluster together (quantified by GARCH; see Section 17). A Gaussian draw treats each day as independent.
- **Autocorrelation:** Returns show negative short-term autocorrelation (mean reversion) and positive momentum at medium horizons.

### 16.2 The Block Bootstrap algorithm

Instead of generating synthetic shocks, we directly resample from the ticker's own observed return history $\{r_1, r_2, \ldots, r_N\}$:

```
For each of 1,000 simulated paths:
  prices = [current_price]
  For each of ⌈252/5⌉ blocks:
    start_idx = random integer in [0, N - block_size)
    block = r[start_idx : start_idx + 5]     ← 5 consecutive real returns
    For each r in block:
      prices.append(prices[-1] * (1 + r))
  return prices[:253]                         ← exactly 252 trading days
```

By sampling **contiguous 5-day blocks**, we preserve:
- The autocorrelation structure within a week
- Volatility clustering (a crash block stays a crash block)
- Fat tails (the actual crash events are in the pool)

The result is a distribution of 1,000 year-end prices from which we extract the 5th, 25th, 50th, 75th, and 95th percentiles for the Capital Deployment Scenarios table.

### 16.3 Black Swan scenario blending

When a Black Swan toggle is active, the return pool is **replaced** with the real historical returns from that crash window (e.g., `^NSEI` daily returns from 2008-01-01 to 2009-03-31). The bootstrap then resamples exclusively from those crash-period returns. Both the chart overlay and the percentile table are recomputed from the new paths — they are always consistent with each other.

---

## 17. GARCH Volatility Modelling

### 17.1 Why GARCH

The 20-day rolling standard deviation of returns (`Volatility_20`) is a simple historical volatility estimate. GARCH (Generalised Autoregressive Conditional Heteroskedasticity) is a more sophisticated model that accounts for the fact that **volatility itself is time-varying and autocorrelated** — high-volatility periods tend to be followed by high-volatility periods.

### 17.2 The GARCH(1,1) model

$$\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$

Where:
- $\sigma_t^2$ is today's conditional variance
- $\omega > 0$ is a long-run variance baseline
- $\alpha \geq 0$ captures how much yesterday's squared shock $\epsilon_{t-1}^2$ affects today's variance (ARCH effect)
- $\beta \geq 0$ captures persistence — how much yesterday's variance carries over
- The stability condition requires $\alpha + \beta < 1$

The constraint $\alpha + \beta < 1$ ensures the process is covariance-stationary (variance doesn't blow up to infinity).

### 17.3 In our codebase

```python
v = arch_model(rets, vol='Garch', p=1, q=1).fit(disp='off').conditional_volatility.iloc[-1] / 100
```

`rets` is the daily return series in percentage points. `conditional_volatility.iloc[-1]` gives today's estimated daily volatility $\hat{\sigma}_t$. Dividing by 100 converts from percentage to decimal. If GARCH fitting fails (too little data, or degenerate series), the system falls back to `Volatility_20`.

---

## 18. Risk Metrics: Sharpe, Sortino, VaR, Max Drawdown

### 18.1 Sharpe Ratio

The Sharpe Ratio measures **risk-adjusted return** — how much return you earn per unit of total risk (standard deviation):

$$\text{Sharpe} = \frac{E[R_{\text{strategy}}] - R_f}{\sigma_{\text{strategy}}} \cdot \sqrt{252}$$

In our implementation, the risk-free rate $R_f$ is approximated as 0 (conservative). The annualisation factor $\sqrt{252}$ converts daily figures to annual. A Sharpe above 1.0 is generally considered good; above 2.0 is excellent.

```python
sharpe = (strat_ret.mean() / strat_ret.std()) * np.sqrt(252)
```

The "strategy" return is the backtest strategy return: holding when the model predicts up, staying out when it predicts down.

### 18.2 Sortino Ratio

The Sortino Ratio is a refinement of Sharpe that only penalises **downside** volatility:

$$\text{Sortino} = \frac{E[R] - R_f}{\sigma_{\text{downside}}} \cdot \sqrt{252}$$

$$\sigma_{\text{downside}} = \sqrt{\frac{1}{N} \sum_{r_t < 0} r_t^2}$$

Only negative daily returns enter the denominator. This is more appropriate for assets with positively skewed return distributions (they should not be penalised for upside volatility).

```python
down_std = data['Daily_Return'][data['Daily_Return'] < 0].std() * np.sqrt(252)
sortino   = data['Daily_Return'].mean() * 252 / down_std
```

### 18.3 Historical VaR (Value at Risk)

$$\text{VaR}_{95\%} = \text{Percentile}_{5\%}(\{r_1, r_2, \ldots, r_N\}) \times 100$$

This is the **Historical Simulation** method. It says: "In 95% of trading days historically, the loss did not exceed this percentage." A VaR of −2.1% means: on the worst 5% of days, this asset lost 2.1% or more.

Historical VaR requires no distributional assumption — it directly reads off the empirical return distribution, preserving fat tails.

### 18.4 Maximum Drawdown

Maximum Drawdown (Max DD) measures the largest peak-to-trough decline in the strategy's equity curve:

$$\text{MaxDD} = \min_t \left( \frac{\text{Equity}_t - \max_{s \leq t} \text{Equity}_s}{\max_{s \leq t} \text{Equity}_s} \right) \times 100$$

Expressed as a percentage. A Max DD of −25% means: at the worst point, the portfolio had fallen 25% from its previous peak. This is often more psychologically relevant than volatility — it tells you the worst historical pain you would have experienced holding this strategy.

```python
roll_max = bt['Strategy_Equity'].cummax()
max_dd   = ((bt['Strategy_Equity'] - roll_max) / roll_max).min() * 100
```

---

## 19. Piotroski F-Score: Fundamental Analysis

### 19.1 Background

The Piotroski F-Score was introduced by Joseph Piotroski in his 2000 paper *"Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers."* It assigns 0 or 1 for each of 9 binary criteria derived from a company's annual financial statements. The total score ranges from 0 (weakest) to 9 (strongest).

Academic research has shown that a simple long/short strategy — buying stocks with F-Score ≥ 8 and shorting those with F-Score ≤ 2 — generated statistically significant abnormal returns in US markets.

### 19.2 The nine criteria

**Profitability (4 signals):**
| # | Criterion | Scores 1 if... |
|---|---|---|
| F1 | ROA (Return on Assets) | Net Income / Total Assets > 0 in current year |
| F2 | Operating Cash Flow | Operating Cash Flow > 0 |
| F3 | Change in ROA | ROA improved year-over-year |
| F4 | Accruals (quality of earnings) | Operating Cash Flow > Net Income (cash earnings > accounting earnings) |

**Leverage, Liquidity & Source of Funds (3 signals):**
| # | Criterion | Scores 1 if... |
|---|---|---|
| F5 | Change in Leverage | Total Debt / Total Assets ratio decreased year-over-year |
| F6 | Change in Liquidity | Current Ratio (Current Assets / Current Liabilities) improved |
| F7 | No Dilution | Shares outstanding did not increase (no equity dilution) |

**Operating Efficiency (2 signals):**
| # | Criterion | Scores 1 if... |
|---|---|---|
| F8 | Change in Gross Margin | Gross Profit / Revenue improved year-over-year |
| F9 | Change in Asset Turnover | Revenue / Total Assets ratio improved year-over-year |

### 19.3 Interpretation

| Score | Interpretation |
|---|---|
| 8–9 | Financially strong — low default risk, improving efficiency |
| 5–7 | Neutral — monitor for trend direction |
| 0–3 | Financially weak — distress signals present |

> **Limitation for Indian markets:** yfinance data for NSE/BSE tickers sometimes has incomplete financial statements, especially for smaller companies. When any core statement (financials, balance sheet, cashflow) is empty, `compute_piotroski()` returns `None` and the UI shows "N/A". ETFs and indices always return N/A — they have no income statements.

---

## 20. Signal Generation and Risk Gates

### 20.1 Base signal from XGBoost projection

The 7-day projected return `pr` is computed from the XGBoost ghost path:

$$pr = \frac{\text{GhostPrice}_7 - \text{Close}_{\text{today}}}{\text{Close}_{\text{today}}} \times 100$$

```python
if pr > 5 and sentiment > 0:   sig = "STRONG BUY 🟢"
elif pr > 1.5:                  sig = "BUY ↗️"
elif pr < -5 and sentiment < 0: sig = "STRONG SELL 🔴"
elif pr < -1.5:                 sig = "SELL ↘️"
else:                           sig = "HOLD ➖"
```

### 20.2 Risk gate — the overrides

After the base signal is set, the risk gate checks three independent conditions:

```python
risky = (
    ("BEAR" in market_mode and sharpe < 0) or   # bear market + negative Sharpe
    (max_dd <= -20) or                           # catastrophic drawdown history
    (sharpe < -0.5)                              # strongly negative risk-adjusted return
)
if risky and "BUY" in sig:
    sig = "HOLD ➖"
```

**Market mode** is defined as:
- `BULL 🐂` if `Close > SMA_50`
- `BEAR 🐻` if `Close ≤ SMA_50`

This means a ticker with a 6% projected gain cannot show STRONG BUY if:
- It is below its 50-day SMA AND historically had negative Sharpe, OR
- Its historical drawdown exceeded −20%, OR
- Its Sharpe is below −0.5

The gate is deliberately conservative. False negatives (missing a real buy opportunity) are preferred over false positives (recommending a buy into a collapsing asset).

---

## 21. SIP Calculator: Time Value of Money

### 21.1 Future Value of a SIP

A Systematic Investment Plan (SIP) is a fixed monthly investment. The future value is:

$$FV = P \cdot \frac{(1 + r)^n - 1}{r} \cdot (1 + r)$$

Where:
- $P$ = monthly investment amount
- $r$ = monthly interest rate = $\text{CAGR} / 12$
- $n$ = total number of months = years × 12
- The extra $(1 + r)$ factor accounts for payments made at the beginning of each period (annuity due)

### 21.2 Time to reach a goal

Inverting the formula to find $n$ given a target corpus $G$:

$$n = \frac{\ln\!\left(1 + \frac{G \cdot r}{P \cdot (1 + r)}\right)}{\ln(1 + r)}$$

This tells you exactly how many months of a given SIP amount, at the ticker's own 5-year CAGR, are required to reach your target.

> **Key design decision:** We use the ticker's own verified 5-year CAGR — not a generic assumption like "12% per year." This means the calculator gives different (and more honest) answers for different assets.

---

## 22. Sentiment Analysis: VADER

### 22.1 What VADER is

VADER (Valence Aware Dictionary and sEntiment Reasoner) is a lexicon and rule-based sentiment analysis tool built specifically for **short social media texts and financial headlines**. Unlike trained ML sentiment models, it requires no training data and runs entirely offline.

### 22.2 How it works

VADER maintains a lexicon of words mapped to valence scores (e.g., "great" → +3.1, "terrible" → −2.5). It applies hand-crafted rules for:
- **Capitalisation:** "GREAT" scores higher than "great"
- **Punctuation:** "great!!!" scores higher than "great"
- **Negation:** "not great" flips the sign
- **Degree modifiers:** "extremely great" amplifies the score

The **compound score** is a normalised sum of all valence scores, bounded to $[-1, +1]$.

### 22.3 How we use it

```python
scores = [analyzer.polarity_scores(n['title'])['compound'] for n in news if 'title' in n]
return float(sum(scores) / len(scores))
```

We average the compound score across all recent news headlines for the ticker. This average feeds into:
1. The signal gate (negative sentiment blocks STRONG BUY)
2. The "News Sentiment Score" metric in the Company Snapshot panel
3. The Screener filter ("Bullish" / "Bearish" / "All")

---


---

# PART 4 — ADVANCED OPERATIONS

## 23. Customising assets.json

`assets.json` defines every ticker the system tracks. The structure is:

```json
{
  "category_name": {
    "subcategory_name": ["TICKER1", "TICKER2"]
  }
}
```

**Ticker format rules:**
| Exchange | Suffix | Example |
|---|---|---|
| NSE (India) | `.NS` | `RELIANCE.NS` |
| BSE (India) | `.BO` | `RELIANCE.BO` |
| US Equities | none | `AAPL` |
| US Indices | `^` prefix | `^GSPC` (S&P 500) |
| Crypto | `-USD` suffix | `BTC-USD` |
| Forex | `=X` suffix | `USDINR=X` |

**Validate after editing:**
```bash
python -c "import json; json.load(open('assets.json')); print('Valid JSON')"
```

> Adding many tickers increases compile time significantly. Each ticker requires a network fetch, XGBoost training, LSTM training, and Monte Carlo simulation. As a guide: 30 tickers ≈ 15–30 minutes on first run.

---

## 24. Bayesian Hyperparameter Tuning (Optuna)

### 24.1 Why tune

The default XGBoost hyperparameters work reasonably for all assets. But each asset has its own volatility profile, data density, and signal structure. Optuna searches for the combination of parameters that maximises holdout $R^2$ for each specific ticker.

### 24.2 Running the tuner

```bash
source jarvis_env/bin/activate
python hyperparameter_tuning.py
```

Run this in a dedicated terminal (or `tmux` session). It runs hundreds of trials per ticker and can take hours. Results are written to `data_lake/hyperparams.json`.

### 24.3 How Bayesian optimisation works

Optuna uses the **TPE (Tree-structured Parzen Estimator)** algorithm. Instead of random search, it builds a probabilistic model of the relationship between hyperparameters and the objective function:

$$\text{score} = \frac{p(x | \text{good trials})}{p(x | \text{bad trials})}$$

Where $p(x | \text{good})$ is a kernel density estimate of hyperparameter values that led to good results, and $p(x | \text{bad})$ is the same for bad results. New trials are proposed by maximising this ratio — sampling from regions known to produce good results.

This is far more efficient than grid search (exhaustive) or random search (no learning across trials).

### 24.4 Parameters searched

| Parameter | Search Range | Effect |
|---|---|---|
| `n_estimators` | 500–3000 | Number of trees; more = slower but potentially better |
| `learning_rate` | 0.005–0.3 | Shrinkage per tree; lower = needs more trees |
| `max_depth` | 3–10 | Tree depth; deeper = more complex patterns |
| `subsample` | 0.5–1.0 | Row sampling; < 1 prevents overfitting |
| `colsample_bytree` | 0.5–1.0 | Feature sampling per tree |

The tuned values are hot-reloaded by the backend on the next cycle. You do not need to restart.

---

## 25. REST API Reference

The FastAPI server runs on `http://localhost:8000`. All `/api/v1/*` endpoints require:

```
X-API-Key: <your QUANT_API_KEY>
```

### Endpoints

**`GET /`** — Health check (no auth required)
```bash
curl http://localhost:8000/
# Response: {"status": "online", "message": "JARVIS-V6 API Server"}
```

**`GET /api/v1/predictions`** — All current predictions
```bash
curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/predictions
```
Returns an array of prediction objects. Each includes the full `JSON_Blob` with Monte Carlo paths, ghost arrays, signal, risk metrics, and fundamentals.

**`GET /api/v1/asset/{ticker}`** — Single asset full breakdown
```bash
curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/asset/RELIANCE.NS
```
Returns the complete prediction record for one ticker.

**`GET /api/v1/leaderboard`** — Summary leaderboard
```bash
curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/leaderboard
```
Returns the condensed leaderboard table.

### Error codes
| Code | Meaning |
|---|---|
| 200 | Success |
| 401 | Missing or invalid `X-API-Key` |
| 404 | Ticker not found in predictions |
| 503 | `QUANT_API_KEY` not set on server, or database not ready |

### Example: Discord bot integration

```python
import requests

API_BASE = "http://localhost:8000/api/v1"
HEADERS  = {"X-API-Key": "your_secure_api_key"}

def get_signal(ticker):
    r = requests.get(f"{API_BASE}/asset/{ticker}", headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        blob = data["JSON_Blob"]
        return f"{ticker}: {blob['Signal']} | Sharpe: {blob['Sharpe']:.2f}"
    return f"Error {r.status_code}"

print(get_signal("RELIANCE.NS"))
```

---

## 26. Troubleshooting Guide

### 26.1 System stuck at "Calculating..." during boot

**Cause:** The backend crashed silently during import or `assets.json` is malformed.

```bash
# Check if backend is running
ps aux | grep stock_market_backend.py

# If not running, run manually to see the error
source jarvis_env/bin/activate
python stock_market_backend.py
```

Common causes:
- `assets.json` has a trailing comma (invalid JSON)
- A required library failed to install (check `logs/backend.log`)
- OpenMP thread collision between PyTorch and XGBoost — fix: add `OMP_NUM_THREADS=1` before the `nohup` line in `stock_market_boot.sh`

### 26.2 UI shows "Failed to load prediction JSON"

**Cause:** The `predictions` table in `quant.db` is empty or corrupted.

```bash
# Inspect the database
source jarvis_env/bin/activate
python -c "
import sqlite3
conn = sqlite3.connect('data_lake/quant.db')
print('Rows in predictions:', conn.execute('SELECT COUNT(*) FROM predictions').fetchone()[0])
print('Rows in historical_data:', conn.execute('SELECT COUNT(*) FROM historical_data').fetchone()[0])
"

# If the DB is corrupted, delete and let the backend recreate it
rm -f data_lake/quant.db
./stock_market_boot.sh
```

### 26.3 "HTTP Error 429 Too Many Requests" in backend.log

**Cause:** Yahoo Finance rate-limited your IP. You are fetching too many tickers too quickly.

**Fix:** The system already has per-ticker timeouts. Wait 15–30 minutes and restart. If it persists:
- Reduce the number of tickers in `assets.json`
- Consider adding a `time.sleep(2)` between tickers in `fetch_and_store()` (not done by default to avoid making full cycles very slow)

### 26.4 Port already in use

```bash
# Find what is using Streamlit's port
lsof -i :8501
kill -9 <PID>

# Find what is using FastAPI's port
lsof -i :8000
kill -9 <PID>

# Or kill all at once
pkill -f stock_market_backend.py
pkill -f stock_market_ui.py
pkill -f uvicorn
```

### 26.5 Database locked errors

```bash
# Add WAL mode to init_db() in stock_market_backend.py:
# conn.execute('PRAGMA journal_mode=WAL')
```

WAL (Write-Ahead Logging) allows the Streamlit UI to read while the backend is writing. Without it, the default SQLite journal mode exclusively locks the file during writes.

### 26.6 Piotroski Score shows N/A for all stocks

**Cause:** yfinance's `.financials`, `.balance_sheet`, or `.cashflow` returned empty DataFrames. This is common for:
- ETFs (no income statements)
- Indices (no financials)
- Recently listed companies (< 2 years of statements)
- Some smaller NSE-listed companies with incomplete yfinance coverage

This is expected behaviour. The system logs the issue and continues. The rest of the analysis is unaffected.

### 26.7 LSTM ghost path is missing from the chart

**Cause:** `train_lstm()` returned `(None, None)`. This happens when there are fewer than 100 training sequences (typically < 200 days of data after dropna).

The system falls back gracefully — only the XGBoost ghost is shown. No error is raised.

### 26.8 SIP calculator shows "CAGR not available"

**Cause:** The ticker has fewer than 200 days of price history in `historical_data`, which is the minimum required for a meaningful CAGR calculation. Newly added tickers may show this for the first cycle until 5 years of data accumulates.

---

## Appendix: Key File Reference

| File | Purpose |
|---|---|
| `stock_market_boot.sh` | Orchestrator: env setup, boot order, progress bar, mode selection |
| `stock_market_backend.py` | Shadow engine: data fetch, ML training, signals, DB writes |
| `stock_market_ui.py` | Streamlit dashboard: investor + advanced panels, portfolio tracker |
| `api_server.py` | FastAPI REST server with X-API-Key auth |
| `hyperparameter_tuning.py` | Optuna Bayesian search for XGBoost params |
| `assets.json` | Ticker list by category and subcategory |
| `requirements.txt` | Pinned Python dependencies |
| `secrets.toml.example` | Template for `.streamlit/secrets.toml` |
| `data_lake/quant.db` | SQLite state manager (auto-created) |
| `data_lake/hyperparams.json` | Tuned XGBoost params (auto-created by tuner) |
| `data_lake/.ready` | Sentinel file written after each full cycle |
| `logs/backend.log` | Backend stdout/stderr |
| `logs/picks.log` | Structured signal log with timestamps |

---

*Trust the math. Respect the risk. Never blindly follow an algorithm.*

*— mrQhere*

