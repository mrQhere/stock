#!/bin/bash
# Copyright (c) 2026 mrQhere. All rights reserved.

BASE_DIR="$(pwd)"

# ==========================================
# STARTUP CHECKLIST
# ==========================================
echo -e ""
echo -e "\033[0;36m╔══════════════════════════════════════════════════════════╗\033[0m"
echo -e "\033[0;36m║       Stock Market Predictor — Boot Checklist            ║\033[0m"
echo -e "\033[0;36m╚══════════════════════════════════════════════════════════╝\033[0m"
echo -e ""
echo -e "\033[0;37mServices that will start:\033[0m"
echo -e "  \033[0;32m[1]\033[0m Backend engine    — ML training, data sync, signal gen"
echo -e "  \033[0;32m[2]\033[0m FastAPI server     — REST API on http://localhost:8000"
echo -e "  \033[0;32m[3]\033[0m Streamlit UI       — Dashboard on http://localhost:8501"
echo -e ""
echo -e "\033[0;37mFiles that will be created (if first run):\033[0m"
echo -e "  \033[0;33m[•]\033[0m stock_env/         — Python virtual environment"
echo -e "  \033[0;33m[•]\033[0m data_lake/quant.db — SQLite database (WAL mode)"
echo -e "  \033[0;33m[•]\033[0m logs/backend.log   — Backend stdout/stderr"
echo -e "  \033[0;33m[•]\033[0m logs/api.log       — FastAPI stdout/stderr"
echo -e ""
echo -e "\033[0;37mOptional (Hermes LLM — auto-detected):\033[0m"
if curl -s http://localhost:11434/ > /dev/null 2>&1; then
    echo -e "  \033[0;32m[✓]\033[0m Ollama is running — Hermes AI analysis ENABLED"
else
    echo -e "  \033[0;33m[✗]\033[0m Ollama not detected — Hermes AI analysis DISABLED (run: ollama serve)"
fi
echo -e ""

# ==========================================
# PHASE 0: ZERO-FRICTION SETUP
# ==========================================
echo -e "\033[0;36m[Phase 0] Checking system dependencies...\033[0m"

check_and_install_sys_deps() {
    local missing=0
    for cmd in python3 pip; do
        if ! command -v $cmd &> /dev/null; then
            echo -e "\033[0;33m  $cmd is missing.\033[0m"
            missing=1
        fi
    done

    if ! python3 -m venv --help &> /dev/null; then
        echo -e "\033[0;33m  python3-venv is missing.\033[0m"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        echo -e "\033[0;33m  Attempting to install missing system dependencies...\033[0m"
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv build-essential
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3 python3-pip gcc gcc-c++
        elif command -v pacman &> /dev/null; then
            sudo pacman -Sy --noconfirm python python-pip base-devel
        else
            echo -e "\033[0;31m  Could not detect package manager. Install python3, pip, and python3-venv manually.\033[0m"
            exit 1
        fi
    else
        echo -e "\033[0;32m  System dependencies OK\033[0m"
    fi
}

check_and_install_sys_deps

if [ ! -d "$BASE_DIR/stock_env" ]; then
    echo -e "\033[0;33m[Phase 0] Virtual environment missing — creating stock_env...\033[0m"
    python3 -m venv "$BASE_DIR/stock_env"

    echo -e "\033[0;33m[Phase 0] Installing dependencies (first run — ~10 minutes)...\033[0m"
    source "$BASE_DIR/stock_env/bin/activate"
    pip install --upgrade pip -q

    echo -e "\033[0;36m  Installing PyTorch CPU wheels (skips 2 GB CUDA download)...\033[0m"
    pip install torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu -q

    req_file="$BASE_DIR/requirements.txt"
    echo -e "\033[0;36m  Installing from requirements.txt...\033[0m"
    if pip install -r "$req_file" -q; then
        echo -e "\033[0;32m  Dependencies installed.\033[0m"
    else
        echo -e "\033[0;33m  Primary install failed. Retrying with fallback flags...\033[0m"
        if pip install -r "$req_file" --no-cache-dir -q; then
            echo -e "\033[0;32m  Installed (--no-cache-dir).\033[0m"
        elif pip install -r "$req_file" --prefer-binary -q; then
            echo -e "\033[0;32m  Installed (--prefer-binary).\033[0m"
        elif pip install -r "$req_file" -i https://pypi.python.org/simple/ -q; then
            echo -e "\033[0;32m  Installed (alternate mirror).\033[0m"
        else
            echo -e "\033[0;31m  CRITICAL: Failed to install requirements. Check your internet connection.\033[0m"
        fi
    fi

    deactivate
    echo -e "\033[0;32m[Phase 0] Environment ready: stock_env/\033[0m"
else
    echo -e "\033[0;32m[Phase 0] stock_env/ exists — skipping install\033[0m"
fi

if [ ! -f "$BASE_DIR/assets.json" ]; then
    echo -e "\033[0;31m[ERROR] assets.json not found. Cannot determine tickers.\033[0m"
    exit 1
fi

# ==========================================
# PHASE 0.5: CREDENTIALS SETUP
# ==========================================
echo -e ""
echo -e "\033[0;36m[Phase 0.5] Checking credentials...\033[0m"

# 1. UI Password
mkdir -p "$BASE_DIR/.streamlit"
SECRETS_FILE="$BASE_DIR/.streamlit/secrets.toml"
if [ ! -f "$SECRETS_FILE" ] || ! grep -q "APP_PASSWORD" "$SECRETS_FILE"; then
    echo -e "\033[0;33m[!] Dashboard Password not set.\033[0m"
    if [ "$CI" = "true" ] || [ ! -t 0 ]; then
        echo -e "\033[0;33m  Non-interactive mode detected. Auto-generating dashboard password.\033[0m"
        USER_APP_PASS="auto-gen-ci-pass"
    else
        read -s -p "Enter a strong password for the UI Dashboard: " USER_APP_PASS
        echo ""
    fi
    echo "APP_PASSWORD = \"$USER_APP_PASS\"" > "$SECRETS_FILE"
    echo -e "\033[0;32m  Saved to $SECRETS_FILE\033[0m"
else
    echo -e "\033[0;32m  Dashboard password OK\033[0m"
fi

# 2. REST API Key
# Check if it's exported in the environment OR stored in ~/.bashrc
BASHRC_FILE="$HOME/.bashrc"
if [ -z "$QUANT_API_KEY" ]; then
    if grep -q "export QUANT_API_KEY=" "$BASHRC_FILE"; then
        # Extract from bashrc and export it for this session
        export QUANT_API_KEY=$(grep -m 1 "^export QUANT_API_KEY=" "$BASHRC_FILE" | cut -d '"' -f 2)
        echo -e "\033[0;32m  REST API Key loaded from $BASHRC_FILE\033[0m"
    else
        echo -e "\033[0;33m[!] REST API Key not set.\033[0m"
        if [ "$CI" = "true" ] || [ ! -t 0 ]; then
            echo -e "\033[0;33m  Non-interactive mode detected. Auto-generating API key.\033[0m"
            USER_API_KEY="auto-gen-ci-key"
        else
            read -s -p "Enter a strong API Key for the FastAPI backend: " USER_API_KEY
            echo ""
        fi
        echo "export QUANT_API_KEY=\"$USER_API_KEY\"" >> "$BASHRC_FILE"
        export QUANT_API_KEY="$USER_API_KEY"
        echo -e "\033[0;32m  Saved to $BASHRC_FILE\033[0m"
    fi
else
    echo -e "\033[0;32m  REST API Key OK (from env)\033[0m"
    # Make sure it's in bashrc for future manual runs
    if ! grep -q "export QUANT_API_KEY=" "$BASHRC_FILE"; then
        echo "export QUANT_API_KEY=\"$QUANT_API_KEY\"" >> "$BASHRC_FILE"
    fi
fi

# ==========================================
# PHASE 1: BACKEND IGNITION
# ==========================================
echo -e ""
echo -e "\033[0;36m[Phase 1] Stopping any previous instances...\033[0m"
pkill -f stock_market_backend.py 2>/dev/null
pkill -f stock_market_ui.py 2>/dev/null
pkill -f uvicorn 2>/dev/null

# Remove old ready flag to force UI to wait for fresh data.
# If a prior run crashed mid-cycle the flag may be stale — delete it
# unconditionally so the UI never starts before the new cycle finishes.
if [ -f "$BASE_DIR/data_lake/.ready" ]; then
    READY_TS=$(cat "$BASE_DIR/data_lake/.ready" 2>/dev/null)
    NOW_TS=$(date +%s)
    # bc may not be installed; use Python for arithmetic
    READY_AGE=$("$BASE_DIR/stock_env/bin/python" -c "print(max(0, $NOW_TS - int(float('$READY_TS'))))" 2>/dev/null || echo 99999)
    if [ -n "$READY_AGE" ] && [ "$READY_AGE" -gt 3600 ] 2>/dev/null; then
        echo -e "\033[0;33m[Phase 1] .ready flag is ${READY_AGE}s old (stale). Deleting...\033[0m"
    else
        echo -e "\033[0;33m[Phase 1] Removing previous .ready flag to ensure fresh data sync.\033[0m"
    fi
    rm -f "$BASE_DIR/data_lake/.ready"
fi

# Create logs and data_lake directories
mkdir -p "$BASE_DIR/logs"
mkdir -p "$BASE_DIR/data_lake"

echo -e "\033[0;36m[Phase 1] Starting services...\033[0m"
echo -e "  \033[0;35m→ Backend:    logs/backend.log\033[0m"
echo -e "  \033[0;35m→ API Server: http://localhost:8000  →  logs/api.log\033[0m"
echo -e "  \033[0;35m→ UI:         http://localhost:8501  (after data sync)\033[0m"

PYTHONUNBUFFERED=1 nohup "$BASE_DIR/stock_env/bin/python" "$BASE_DIR/src/stock_market_backend.py" > "$BASE_DIR/logs/backend.log" 2>&1 &
nohup "$BASE_DIR/stock_env/bin/uvicorn" src.api_server:app --host 0.0.0.0 --port 8000 > "$BASE_DIR/logs/api.log" 2>&1 &

sleep 2
if ! pgrep -f stock_market_backend.py > /dev/null; then
    echo -e "\033[0;31m[ERROR] Backend failed to start. Last 20 lines of logs/backend.log:\033[0m"
    tail -20 "$BASE_DIR/logs/backend.log"
    exit 1
fi
echo -e "\033[0;32m[Phase 1] Backend running ✓\033[0m"

# ==========================================
# PHASE 2: DATA SYNCHRONIZATION
# ==========================================
echo -e ""
echo -e "\033[0;36m[Phase 2] Waiting for all tickers to complete first cycle...\033[0m"

DB_FILE="$BASE_DIR/data_lake/quant.db"

TOTAL_TICKERS=$("$BASE_DIR/stock_env/bin/python" -c "import json; d=json.load(open('$BASE_DIR/assets.json')); print(sum(len(v) for cat in d.values() for v in cat.values()))" 2>/dev/null)
if [ -z "$TOTAL_TICKERS" ] || [ "$TOTAL_TICKERS" -eq 0 ]; then TOTAL_TICKERS=30; fi

START_TIME=$(date +%s)

while [ ! -f "$BASE_DIR/data_lake/.ready" ]; do
    if ! pgrep -f stock_market_backend.py > /dev/null; then
        echo -e "\n\033[0;31m[CRITICAL] Backend died during sync. Check logs/backend.log:\033[0m"
        tail -20 "$BASE_DIR/logs/backend.log"
        exit 1
    fi

    PROCESSED=$("$BASE_DIR/stock_env/bin/python" -c "
import sqlite3
try:
    conn = sqlite3.connect('$DB_FILE')
    print(conn.execute('SELECT COUNT(*) FROM predictions').fetchone()[0])
except Exception:
    print(0)
" 2>/dev/null)
    PROCESSED=${PROCESSED:-0}

    CURR_TIME=$(date +%s)
    ELAPSED=$((CURR_TIME - START_TIME))

    if [ "$PROCESSED" -gt 0 ]; then
        AVG_TIME=$((ELAPSED / PROCESSED))
        if [ "$AVG_TIME" -eq 0 ]; then AVG_TIME=1; fi
        REMAINING=$((TOTAL_TICKERS - PROCESSED))
        if [ "$REMAINING" -lt 0 ]; then REMAINING=0; fi
        EST_SEC=$((REMAINING * AVG_TIME))
        EST_MIN=$((EST_SEC / 60))
        EST_REM_SEC=$((EST_SEC % 60))
        EST_MSG="${EST_MIN}m ${EST_REM_SEC}s"
    else
        EST_MSG="Calculating..."
    fi

    if [ "$TOTAL_TICKERS" -gt 0 ]; then
        PCT=$(( PROCESSED * 100 / TOTAL_TICKERS ))
        if [ "$PCT" -gt 100 ]; then PCT=100; fi
    else
        PCT=0
    fi

    DOTS_TOTAL=20
    DOTS_DONE=$(( PCT * DOTS_TOTAL / 100 ))
    DOTS_LEFT=$(( DOTS_TOTAL - DOTS_DONE ))

    BAR="["
    for ((i=0; i<DOTS_DONE; i++)); do BAR="${BAR}#"; done
    for ((i=0; i<DOTS_LEFT; i++)); do BAR="${BAR}."; done
    BAR="${BAR}]"

    echo -ne "\r\033[0;33m  Compiling: ${BAR} ${PCT}% | ${PROCESSED}/${TOTAL_TICKERS} tickers | ETA: ${EST_MSG}  \033[0m"
    sleep 2
done

echo -e "\n\033[0;32m[Phase 2] .ready flag detected. Verifying data integrity...\033[0m"

# After the .ready flag exists, verify the DB actually contains ALL expected
# tickers.  The backend writes .ready only after all tickers finish, but a
# previous-cycle stale flag could race through; this double-check removes any
# remaining ambiguity.
VERIFIED=0
for attempt in 1 2 3 4 5; do
    sleep 2
    DB_COUNT=$("$BASE_DIR/stock_env/bin/python" -c "
import sqlite3
try:
    conn = sqlite3.connect('$DB_FILE')
    count = conn.execute('SELECT COUNT(DISTINCT Ticker) FROM predictions').fetchone()[0]
    print(count)
except Exception:
    print(0)
" 2>/dev/null)
    DB_COUNT=${DB_COUNT:-0}

    if [ "$DB_COUNT" -ge "$TOTAL_TICKERS" ]; then
        echo -e "\033[0;32m  ✓ All $TOTAL_TICKERS tickers verified in database ($DB_COUNT found)\033[0m"
        VERIFIED=1
        break
    else
        echo -e "\033[0;33m  [Retry $attempt/5] Database has $DB_COUNT/$TOTAL_TICKERS tickers — waiting...\033[0m"
    fi
done

if [ $VERIFIED -eq 0 ]; then
    echo -e "\033[0;31m[WARNING] Could not verify all tickers in database after retries.\033[0m"
    echo -e "\033[0;33m  Some tickers may be missing. Launching UI anyway.\033[0m"
fi

echo -e "\033[0;32m[Phase 2] All tickers compiled ✓\033[0m"

# ==========================================
# PHASE 3: MODE SELECTION & UI LAUNCH
# ==========================================
clear

echo -e "\033[0;36m╔══════════════════════════════════════════════════════════╗\033[0m"
echo -e "\033[0;36m║       Stock Market Predictor — Ready                     ║\033[0m"
echo -e "\033[0;36m╚══════════════════════════════════════════════════════════╝\033[0m"
echo -e ""
echo -e "\033[0;32m  ✓ Backend running    (logs/backend.log)\033[0m"
echo -e "\033[0;32m  ✓ API server running (http://localhost:8000)\033[0m"
echo -e "\033[0;32m  ✓ Data sync complete ($TOTAL_TICKERS tickers)\033[0m"
echo -e ""
echo -e "Select mode:"
echo -e "  \033[0;33m1)\033[0m Investor Mode   — fundamentals, Piotroski, SIP calculator"
echo -e "  \033[0;33m2)\033[0m Advanced Mode   — signals, Monte Carlo, backtest, Hermes AI"
read -p "> " MODE_CHOICE
export APP_MODE=$([ "$MODE_CHOICE" == "2" ] && echo "advanced" || echo "investor")
echo -e "\033[0;32mLaunching in ${APP_MODE} mode → http://localhost:8501\033[0m"

TOTAL_TICKERS=$("$BASE_DIR/stock_env/bin/python" -c "import json; d=json.load(open('$BASE_DIR/assets.json')); print(sum(len(v) for cat in d.values() for v in cat.values()))" 2>/dev/null)
export TOTAL_TICKERS

"$BASE_DIR/stock_env/bin/streamlit" run "$BASE_DIR/src/stock_market_ui.py"
