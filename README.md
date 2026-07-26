<div align="center">

# 🟢 Stock Market Predictor & Institutional Quant Terminal

**An autonomous, locally-hosted quantitative analysis engine tailored for Global Equities, Crypto, and Forex.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![XGBoost](https://img.shields.io/badge/AI-XGBoost-orange.svg)](https://xgboost.readthedocs.io/)
[![PyTorch](https://img.shields.io/badge/DeepLearning-PyTorch-red.svg)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)

Designed for researchers and quants, this system fuses traditional tree-based models (XGBoost) with deep sequence learning (LSTM PyTorch), NLP sentiment analysis, and fundamental factor models (Fama-French) into a completely offline, local-first SQLite architecture.

> [!CAUTION]
> **NOT FINANCIAL ADVICE.** This is a highly experimental research tool. Do not deploy real capital trusting these predictions. Markets are fundamentally stochastic, and ML models are highly susceptible to overfitting and black-swan regime changes. 

![Terminal Overview Demo](assets/demo.gif)
*[Watch the full walkthrough on YouTube](https://youtube.com/your-video-link-here)*

</div>

---

## 📑 Table of Contents
- [Core Architecture](#-core-architecture)
- [Why We Built This & Setup](#-why-we-built-this--setup)
- [Advanced Analytics Engine](#-advanced-analytics-engine)
- [Tech Stack](#-tech-stack)

---

## 🏗 Core Architecture
- **Dual AI Engine:** Simultaneously trains XGBoost (tree-based) and PyTorch LSTM (deep sequence learning) models to contrast standard factor logic vs deep time-series patterns.
- **Embedded SQLite Data Lake:** All data, hyperparameter tuning results, and AI states are fully centralized in a local relational database (`quant.db`).
- **Headless FastAPI Layer:** A fully standalone API server allows external programmatic access to the database's ML outputs.
- **Optuna Auto-Tuning:** A dedicated background daemon dynamically optimizes XGBoost hyperparameters per-ticker using Bayesian search.

---

## 🚀 Why We Built This & Setup

Most retail trading platforms hide their algorithms or charge exorbitant fees for basic quantitative metrics. We built the **Stock Market Predictor** as an open-source, local-first alternative for researchers who want full transparency into the data pipeline, model weights, and mathematical logic driving the predictions.

### Prerequisites
- **Python 3.10+** (Required for PyTorch and FastAPI dependencies)
- **Git**
- **NVIDIA GPU (Optional but recommended for PyTorch/CUDA acceleration)**

### Installation
1. **Clone & Boot:**
   ```bash
   chmod +x stock_market_boot.sh
   ./stock_market_boot.sh
   ```
   > **Note:** The boot script handles virtual environment creation, pip installations (including heavy PyTorch binaries), and spins up both the ML backend and the FastAPI server.

2. **Security & Access (Passwords):**
   The terminal is protected by an authentication wall. You must define a password in a Streamlit secrets file before use.
   - Create a file at `.streamlit/secrets.toml`
   - Add your password: `APP_PASSWORD = "your_secure_password"`
   - *This file is ignored by `.gitignore` to prevent credential leaks.*

---

## 🧠 Advanced Analytics Engine

### 1. Market Screener & Factor Exposures
The system features a lightning-fast local screener that queries `quant.db` without hitting external API rate limits. It automatically extracts Fama-French proxies (Size/Market Cap, Value/PB Ratio, Momentum) for advanced portfolio construction.

### 2. Natural Language Processing (NLP) Sentiment
The backend continuously scrapes real-time financial headlines for target tickers using `yfinance` and parses them through a `vaderSentiment` NLP pipeline to calculate a quantitative Bullish/Bearish polarity score.

### 3. Probabilistic Monte Carlo & Interactive Charting
Forecasts are bounded by 1,000-path GARCH volatility Monte Carlo simulations. The frontend UI provides interactive Plotly charting, allowing researchers to draw custom trendlines over the AI's autoregressive 7-day projections.

---

## 🛠️ Tech Stack
| Category | Technology |
|---|---|
| **Deep Learning** | PyTorch (LSTM) |
| **Machine Learning** | XGBoost, Optuna (Bayesian Tuning) |
| **NLP** | vaderSentiment |
| **API & DB** | FastAPI, Uvicorn, SQLite3 |
| **Frontend UI** | Streamlit, Plotly |

---

> [!WARNING]
> **FINAL CAUTION:** This software is provided "as is". Financial markets are highly complex systems. The creator assumes no liability for trading losses incurred from using this tool.
