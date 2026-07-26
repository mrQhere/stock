# Stock Market Predictor: Advanced Researcher Guide

**GitHub Repository:** [mrQhere/stock](https://github.com/mrQhere/stock)

Welcome to the **Stock Market Predictor**. This document serves as the technical manual for operating, tuning, and understanding the mathematical and architectural limits of the platform.

> [!CAUTION]
> **RESEARCH PURPOSES ONLY.** This platform provides mathematical probabilities based on historical data. It cannot predict the future. Do not use this tool to make live trading decisions with real capital.

---

## Table of Contents
1. [Why We Built This & Setup Instructions](#1-why-we-built-this--setup-instructions)
2. [Setting Up Security (Passwords)](#2-setting-up-security-passwords)
3. [System Architecture & Core Loop](#3-system-architecture--core-loop)
4. [The Dual AI Engine (LSTM vs XGBoost)](#4-the-dual-ai-engine-lstm-vs-xgboost)
5. [Factor Analysis & NLP Pipeline](#5-factor-analysis--nlp-pipeline)
6. [Optuna Hyperparameter Studio](#6-optuna-hyperparameter-studio)
7. [FastAPI External Access](#7-fastapi-external-access)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Why We Built This & Setup Instructions

We built the Stock Market Predictor for absolute transparency. Black-box algorithmic trading platforms abstract away their underlying math, leaving researchers unable to verify or tune the predictive models. This platform runs 100% locally on your machine, giving you direct access to the SQLite database, the model weights, and the code driving the analysis.

### Setup Instructions
1. Clone the repository to your local machine.
2. Ensure you have Python 3.10+ installed.
3. Make the boot script executable:
   ```bash
   chmod +x stock_market_boot.sh
   ```
4. Run the boot sequence:
   ```bash
   ./stock_market_boot.sh
   ```
   *The boot sequence will automatically create a virtual environment, install heavy dependencies (like PyTorch and FastAPI), and launch both the ML background engine and the API server.*

---

## 2. Setting Up Security (Passwords)

To prevent unauthorized access to your portfolio and ML data, the UI is gated by an authentication screen. You **must** set a custom password.

1. Ensure the directory `.streamlit` exists in the root folder.
2. Create or edit the file `.streamlit/secrets.toml`.
3. Add the following line:
   ```toml
   APP_PASSWORD = "your_custom_password_here"
   ```
4. Restart the UI. The dashboard will now require this exact password to unlock.
> *Note:* The `.gitignore` has been strictly configured to prevent `.streamlit/secrets.toml` from being uploaded to GitHub.

---

## 3. System Architecture & Core Loop

The platform operates as a decoupled, local-first ecosystem:
- **`stock_market_backend.py` (The Shadow Engine):** An asynchronous daemon that syncs Yahoo Finance data into an embedded SQLite database (`quant.db`), computes 20+ technical indicators, and retrains the ML models on every cycle.
- **`api_server.py` (The Headless Layer):** A FastAPI server (port 8000) that exposes the SQLite database via REST endpoints.
- **`stock_market_ui.py` (The Interface):** A multi-tab Streamlit dashboard (port 8501) comprising the deep-dive Terminal, the mass-market Screener, and the Live Portfolio Tracker.

---

## 4. The Dual AI Engine (LSTM vs XGBoost)

The core forecasting engine relies on an ensemble approach, deliberately pitting a tree-based model against a deep neural network to expose structural biases.

- **XGBoost (Tree-Based):** Excellent at capturing non-linear relationships between specific technical thresholds (e.g., RSI < 30 and MACD crossing). It is highly interpretable via SHAP values.
- **PyTorch LSTM (Deep Sequence):** A Recurrent Neural Network (RNN) tailored for time-series memory. It analyzes the *sequence* of the last 5 days of normalized price action, ignoring absolute values to focus strictly on kinetic momentum.

> **Researcher Note:** If the XGBoost line and the LSTM line diverge wildly on the interactive chart, it signifies high market ambiguity. The models are disagreeing.

---

## 5. Company Snapshot & NLP Pipeline

The platform does not rely solely on technicals. It incorporates fundamental and alternative data constraints to ensure algorithmic signals are anchored in reality:
- **NLP Sentiment:** Real-time Yahoo Finance headlines are parsed through `vaderSentiment`. A negative sentiment score acts as a hard mathematical penalty against algorithmic Buy signals. For instance, a technical "Buy" signal will be capped to a "Hold" if the overarching news sentiment is deeply bearish or if the asset is in a historical drawdown cycle exceeding 20%.
- **Snapshot Metrics:** The system extracts raw company metrics including Market Cap, Price/Book Ratio, and 6M Trailing Momentum. These numbers are purely observational and provide the researcher with immediate context regarding the asset's size and value standing before examining the algorithmic predictions.

---

## 5b. The Block Bootstrap Engine (Monte Carlo)

The most advanced feature of the UI is its approach to risk simulation. Standard quant models use simple Gaussian random walks, which dangerously underestimate the likelihood of massive market crashes (fat tails). 
This tool discards the bell curve. It implements a **Historical Block Bootstrap**, drawing random 5-day continuous blocks from the asset's real trading history to build 1,000 possible future paths.

- **Real Crash Simulation:** On the sidebar, you can overlay real historical crashes (e.g., the 2008 Financial Crisis, the 2020 COVID Panic, and the 2022 Rate Hike). 
- **Dynamic Calibration:** Toggling these scenarios does not just draw a line on the chart; it fundamentally restructures the simulation. The backend blends the return distributions from those exact historical disaster windows into the ticker's probability matrix, dynamically updating the Capital Deployment Scenario tables so you know exactly what your downside risk looks like in a true Black Swan event.

---

## 6. Optuna Hyperparameter Studio

Machine learning models decay. To prevent XGBoost from overfitting to obsolete regimes, we built a standalone Bayesian optimization studio.

Run the optimizer in a separate terminal:
```bash
source jarvis_env/bin/activate
python hyperparameter_tuning.py
```
This script aggressively mutates the XGBoost parameters (`learning_rate`, `max_depth`, `subsample`) across thousands of simulated trials. The absolute best mathematical configuration for *each specific ticker* is saved to `data_lake/hyperparams.json`. The main backend engine hot-reloads these optimal parameters seamlessly.

---

## 7. FastAPI External Access

For algorithmic traders and researchers building external tools, you do not need to open the UI to access the intelligence.

With the boot script running, query the FastAPI server directly:
```bash
# Get all AI predictions and signals
curl -H "X-API-Key: your_secure_api_key" http://localhost:8000/api/v1/predictions

# Get deep ML data for a specific asset
curl -H "X-API-Key: your_secure_api_key" http://localhost:8000/api/v1/asset/AAPL
```
*Note: The `X-API-Key` header is strictly enforced for all data endpoints. You must configure `QUANT_API_KEY` in your environment variables for this to function.*

---

## 8. Troubleshooting

### Port Conflicts
If Streamlit (8501) or FastAPI (8000) fail to bind:
```bash
kill -9 $(lsof -t -i:8501)
kill -9 $(lsof -t -i:8000)
```

### Deep Learning (PyTorch) Memory Leaks
If the backend crashes with CUDA Out of Memory (OOM) errors during the LSTM training phase, downgrade the `hidden_layer_size` in the `LSTMPredictor` class inside `stock_market_backend.py`.

> [!WARNING]
> **REITERATION OF RISK:** The outputs of this software are mathematical probabilities derived from the past. They do not guarantee future returns. Do not trade real money based on this software.
