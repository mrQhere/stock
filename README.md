<div align="center">

#  Stock Market Predictor & Institutional Quant Terminal

**An autonomous, locally-hosted quantitative analysis engine for Global Equities, ETFs, Crypto, Forex, and Indices.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![XGBoost](https://img.shields.io/badge/AI-XGBoost-orange.svg)](https://xgboost.readthedocs.io/)
[![PyTorch](https://img.shields.io/badge/DeepLearning-PyTorch-red.svg)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Repository](https://img.shields.io/badge/GitHub-mrQhere%2Fstock-181717.svg?logo=github)](https://github.com/mrQhere/stock)

Designed for researchers and long-term investors, this system fuses tree-based gradient boosting (XGBoost), deep sequence learning (LSTM/PyTorch), NLP sentiment analysis, Piotroski F-Score fundamental screening, and historical block-bootstrap Monte Carlo into a fully offline, local-first SQLite architecture.

> [!CAUTION]
> **NOT FINANCIAL ADVICE.** This is an experimental research tool. Do not deploy real capital based on these predictions. Markets are stochastic; ML models are susceptible to overfitting and black-swan regime changes.

</div>

---

## 📑 Table of Contents
- [What's New](#-whats-new)
- [Core Architecture](#-core-architecture)
- [Two Modes: Investor & Advanced](#-two-modes-investor--advanced)
- [Setup & Installation](#-setup--installation)
- [Setting Authentication](#-setting-authentication)
- [REST API](#-rest-api-optional)
- [Tech Stack](#-tech-stack)
- [Optional Tools](#-optional-tools)

---

## 🆕 What's New

| Feature | Description |
|---|---|
| **Investor Mode** | Clean dashboard: price snapshot, Piotroski F-Score, full Fundamentals panel, SIP/Goal Calculator — no trading noise |
| **Advanced Mode** | Full quant terminal: AI signals, 7-day projections, Monte Carlo, Sharpe/Drawdown, backtest chart |
| **Piotroski F-Score** | 9-point fundamental health check from real financial statements via yfinance |
| **SIP Calculator** | Goal projections using the ticker's own 5-year CAGR — no hardcoded assumptions |
| **Per-ticker Timeout** | `ThreadPoolExecutor` wraps all compute; one slow ticker can't stall the cycle |
| **Stale-data Fallback** | Failed tickers show previous cycle data with a ⚠ badge instead of disappearing |
| **Real Crash Windows** | 2008 GFC, 2020 COVID, 2022 Rate Hike — actual ^NSEI daily return sequences |
| **CPU-only PyTorch** | Installed from `download.pytorch.org/whl/cpu` — no multi-GB CUDA download |
| **Pinned deps** | All dependencies pinned; `fastapi==0.115.12`, `uvicorn==0.34.3` |

---

## 🏗 Core Architecture

- **Dual AI Engine:** XGBoost (tree-based non-linear thresholds) + PyTorch LSTM (deep sequence autoregression) trained in parallel.
- **Embedded SQLite Data Lake:** All predictions, hyperparameters, and backtest results live in `data_lake/quant.db`. No cloud DB required.
- **Fault-tolerant Backend:** Per-ticker 120s timeout via `ThreadPoolExecutor`. On timeout or error, the previous cycle's result is re-served with a stale flag — no ticker ever vanishes silently.
- **FastAPI Headless Layer:** Secured via `X-API-Key` header on all `/api/v1/*` routes. The root `GET /` health check is exempt.
- **Optuna Auto-Tuning:** Background daemon runs Bayesian hyperparameter search per ticker, hot-reloading results into the next cycle.

---

## 🧭 Two Modes: Investor & Advanced

The boot script prompts you to choose before launching:

```
Select mode:
  1) Simple Long-Term Investor   (fundamentals, Piotroski, SIP calculator)
  2) Advanced Trader             (all panels + signal, Monte Carlo, backtest)
```

You can also flip the **Advanced Mode** toggle in the sidebar at any time — no restart needed. The backend always computes all data; mode is purely a UI rendering decision.

**Investor Mode shows (always visible):**
- Price Snapshot: current price, 1Y return, 5Y CAGR, dividend yield
- Company Snapshot: Market Cap, P/B, 6M momentum, news sentiment
- Fundamentals table: 12 metrics with plain-English explanations per row
- Piotroski F-Score: 0–9 score with colour coding and explanation
- SIP & Goal Calculator: monthly SIP → projected corpus using real CAGR

**Advanced Mode adds:**
- AI Signal (STRONG BUY → STRONG SELL) with risk gate logic
- Sharpe, Max Drawdown, Win Probability, GARCH Volatility
- XGBoost + LSTM 7-day price projections
- Monte Carlo Capital Deployment Scenarios (7D / 1M / 1Y percentile table)
- Black Swan scenario overlays (real crash return data + formula toggles)
- Risk Parity Portfolio weights

---

## 🚀 Setup & Installation

> **Prerequisites:** Linux (Ubuntu 22.04+ recommended), Python 3.12+, Git.

```bash
# 1. Clone the repository
git clone https://github.com/mrQhere/stock.git
cd stock

# 2. Boot everything 
# (The script will interactively ask you to set your passwords on the first run)
chmod +x stock_market_boot.sh
./stock_market_boot.sh
```

The boot script will:
1. Create `stock_env/` virtual environment
2. Install PyTorch CPU wheels (avoids ~2 GB CUDA download)
3. Install all pinned dependencies from `requirements.txt`
4. Launch the backend shadow engine in the background
5. Show a real-time progress bar while all tickers compile
6. Ask you to select Investor or Advanced mode
7. Launch the Streamlit dashboard

> **First run takes 5–15 minutes** depending on your internet speed and the number of tickers in `assets.json`. Subsequent runs use cached data and are near-instant.

---

## 🔐 Setting Authentication

The boot script (`stock_market_boot.sh`) features a **zero-friction interactive setup**. On your very first run, it will prompt you in the terminal to:
1. Create a secure `APP_PASSWORD` for the Streamlit Dashboard.
2. Create a `QUANT_API_KEY` for the REST API.

These are automatically saved to `.streamlit/secrets.toml` and your `~/.bashrc` file respectively. You never have to configure them manually.

---

> **Headless Mode / CI:** Prefix the boot command with `CI=true` (e.g., `CI=true ./stock_market_boot.sh`) to automatically bypass interactive prompts and auto-generate credentials.

> **Forgot your credentials?** Run `./reset_creds.sh` to automatically generate and save a new secure password and API key.

## 🔌 REST API (Optional)

The system includes a FastAPI server that exposes all predictions via HTTP. It starts automatically alongside the backend and UI when you run `./stock_market_boot.sh`.

**Base URL:** `http://localhost:8000`  
**Logs:** `logs/api.log`

All `/api/v1/*` routes require the `X-API-Key` header:

```bash
# Health check (no key required)
curl http://localhost:8000/
# → {"status": "online", "message": "Stock Quant API Server"}

# All current predictions
curl -H "X-API-Key: $QUANT_API_KEY" http://localhost:8000/api/v1/predictions

# Single asset full breakdown
curl -H "X-API-Key: $QUANT_API_KEY" http://localhost:8000/api/v1/asset/RELIANCE.NS

# Summary leaderboard
curl -H "X-API-Key: $QUANT_API_KEY" http://localhost:8000/api/v1/leaderboard
```

For the full API reference including error codes and integration examples, see **USER_GUIDE.md → Section 25**.

---

## 🛠️ Tech Stack

| Category | Technology | Version |
|---|---|---|
| **Deep Learning** | PyTorch (LSTM) | 2.3.1 (CPU) |
| **Machine Learning** | XGBoost | 3.3.0 |
| **Hyperparameter Tuning** | Optuna (Bayesian) | 3.6.1 |
| **LLM Agent** | Ollama + phi3:mini | local |
| **NLP** | vaderSentiment | 3.3.2 |
| **GARCH Volatility** | arch | 8.0.0 |
| **Market Data** | yfinance | 1.5.2 |
| **API & DB** | FastAPI, Uvicorn, SQLite3 | 0.115.12 / 0.34.3 |
| **Frontend UI** | Streamlit, Plotly | 1.60.0 / 6.9.0 |
| **Data** | pandas, numpy | 3.0.5 / 2.5.1 |

---

## 🔬 Optional Tools

### Manual Hyperparameter Tuning

`hyperparameter_tuning.py` is a **standalone offline utility** for researchers who want to run Bayesian optimisation (Optuna) over XGBoost hyperparameters for every ticker in the database.

**Why it's optional:** The backend already reads tuned params from `data_lake/hyperparams.json` if that file exists. This script is for running a deeper, offline search — not a background daemon.

**Prerequisites:** The backend must have completed at least one cycle so `data_lake/quant.db` contains `historical_data` rows.

```bash
source stock_env/bin/activate
python src/hyperparameter_tuning.py
```

Results are written to `data_lake/hyperparams.json`. The backend hot-reloads this file at the start of every new cycle — no restart required.

> [!NOTE]
> This script is not called by `stock_market_boot.sh` and has no automatic scheduling. Run it manually when you want a deeper parameter search (e.g., after adding new tickers or if holdout R² has been degrading).

---

> [!WARNING]
> **FINAL CAUTION:** This software is provided "as is". Financial markets are highly complex, non-stationary systems. The creator assumes no liability for any trading losses incurred from using this tool. Past model performance does not guarantee future results.


---

&copy; 2026 mrQhere. All rights reserved.
