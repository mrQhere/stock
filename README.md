# 🟢 Stock Market Predictor: Sovereign Institutional Quant Terminal

An autonomous, locally-hosted quantitative analysis engine and terminal. Designed for absolute privacy and resource efficiency, this system executes machine learning pipelines, Monte Carlo simulations, and GenAI risk assessments entirely on local hardware without relying on external cloud APIs.

### 🧠 Core Architecture
* **The Shadow Engine (Backend):** A daemonized Python worker running in detached `tmux` sessions. It features an hourly incremental data-lake sync and an automated XGBoost training loop that actively corrects its own hallucination margins using historical R² compatibility scoring.
* **The Vision Suite (Frontend):** A secure, password-gated Streamlit dashboard displaying 6x3 capital deployment matrices, SHAP feature importance, and interactive Plotly charting.
* **Local LLM Integration:** Integrates `Llama-3` via `Ollama` for a localized "AI Council" that reads the mathematical outputs and generates instant 3-sentence risk audits.

### ⚡ Technical Highlights
* **Optimized for Constrained Hardware:** Engineered to run complex GARCH(1,1) volatility models, 1,200-tree XGBoost ensembles, and a 4.7GB LLM simultaneously on just **2 Cores and 8.7GB RAM**.
* **Zero-Telemetry Security:** Built with a "Sovereign First" mindset. All data parsing, AI training, and inference happen locally. Zero data is sent to OpenAI or third-party clouds.
* **Black Swan Stress Testing:** Features 6 dynamic macro-economic overlay models (2008 Crash, Oil War, Hyperinflation, etc.) modifying the 1,000-path Monte Carlo simulations.
* **Sovereign Boot Sequence:** A custom bash ignition script that handles environment activation, daemon resurrection, and secure password gating before deploying the UI.

### 🛠️ Tech Stack
`Python 3` | `XGBoost` | `Streamlit` | `Ollama (Llama-3)` | `yfinance` | `Bash Scripting` | `Tmux`
