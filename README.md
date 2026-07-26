<div align="center">

# 🟢 Stock Market Predictor & Institutional Quant Terminal

**An autonomous, locally-hosted quantitative analysis engine tailored for Global Equities, Crypto, and Forex.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![XGBoost](https://img.shields.io/badge/AI-XGBoost-orange.svg)](https://xgboost.readthedocs.io/)
[![PyTorch](https://img.shields.io/badge/DeepLearning-PyTorch-red.svg)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![GitHub Repository](https://img.shields.io/badge/GitHub-mrQhere%2Fstock-181717.svg?logo=github)](https://github.com/mrQhere/stock)

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
- **Embedded SQLite Data Lake:** All data, hyperparameter tuning results, and AI states are fully centralized in a local relational database (`quant.db`). This ensures that the platform remains entirely self-contained without requiring external cloud databases.
- **Headless FastAPI Layer:** A fully standalone API server allows external programmatic access to the database's ML outputs. It is secured via strict `X-API-Key` headers to ensure your data remains completely private.
- **Optuna Auto-Tuning:** A dedicated background daemon dynamically optimizes XGBoost hyperparameters per-ticker using Bayesian search, preventing the model from becoming stale as market regimes shift over time.

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

2. **Security & Access (Passwords & API Keys):**
   The terminal and API are strictly protected by an authentication wall to prevent unauthorized access. You must define your credentials before use.
   - **For the UI**: Create a file at `.streamlit/secrets.toml` with your password: `APP_PASSWORD = "your_secure_password"`. *(This file is ignored by `.gitignore` to ensure your password is never leaked)*.
   - **For the API**: Set the `QUANT_API_KEY` environment variable on the server before launching. All API requests (except the root health check) must include this key in the `X-API-Key` header.
     - Example: `export QUANT_API_KEY="your_secure_api_key"`
     - Usage: `curl -H "X-API-Key: your_secure_api_key" http://localhost:8000/api/v1/predictions`
   - You can refer to the provided `secrets.toml.example` file for a template configuration.

---

## 🧠 Advanced Analytics Engine

### 1. Market Screener & Snapshot Metrics
The system features a lightning-fast local screener that queries `quant.db` without hitting external API rate limits. It extracts critical snapshot metrics directly from the company's balance sheet, including Market Cap, Price/Book Ratio, and 6M Price Momentum, for advanced portfolio construction and risk parity weighting.

### 2. Natural Language Processing (NLP) Sentiment
The backend continuously scrapes real-time financial headlines for target tickers using `yfinance` and parses them through a `vaderSentiment` NLP pipeline to calculate a quantitative Bullish/Bearish polarity score. This score acts as an algorithmic risk gate, immediately blocking anomalous BUY signals if the overall market sentiment is overtly bearish.

### 3. Historical Block Bootstrap & Real Crash Windows
Traditional Monte Carlo simulations falsely assume market returns follow a smooth Gaussian bell curve, completely ignoring the fat-tailed reality of black swan events. To solve this, the Stock Market Predictor uses a **5-day Historical Block Bootstrap**. 
- It simulates thousands of 252-day forward paths by randomly sampling 5-day chunks from the ticker's *actual* historical returns, perfectly preserving the asset's true volatility clustering and autocorrelation.
- **Real Black Swan Data:** The UI dynamically pulls real daily crash data from the `^NSEI` benchmark index for the 2008 Global Financial Crisis, the 2020 COVID Crash, and the 2022 Rate Hike Selloff.
- **Dynamic Blending:** When you toggle a Black Swan scenario in the UI, the simulation instantaneously rebuilds its return pool from those exact historical periods and recalculates the Capital Deployment Percentile thresholds (7-Day, 1-Month, 1-Year).

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
