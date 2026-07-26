#!/bin/bash

BASE_DIR="$(pwd)"

# ==========================================
# PHASE 0: ZERO-FRICTION SETUP
# ==========================================
echo -e "\033[0;36mInitializing Zero-Friction Setup...\033[0m"

if [ ! -d "$BASE_DIR/jarvis_env" ]; then
    echo -e "\033[0;33mVirtual Environment missing. Creating one now...\033[0m"
    python3 -m venv "$BASE_DIR/jarvis_env"
    
    echo -e "\033[0;33mInstalling AI & UI dependencies (this may take a minute)...\033[0m"
    source "$BASE_DIR/jarvis_env/bin/activate"
    pip install --upgrade pip
    pip install yfinance pandas numpy xgboost arch scikit-learn streamlit plotly pytz
    deactivate
    echo -e "\033[0;32mEnvironment setup complete!\033[0m"
fi

if [ ! -f "$BASE_DIR/assets.json" ]; then
    echo -e "\033[0;33mNo assets.json found. Creating default portfolio...\033[0m"
    cat << 'EOF' > "$BASE_DIR/assets.json"
{
  "Large Cap": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"],
  "Mid Cap": ["TATAPOWER.NS", "IRCTC.NS", "ZOMATO.NS"],
  "Indices": ["^NSEI", "^NSEBANK"]
}
EOF
fi

# ==========================================
# PHASE 1: BACKEND IGNITION
# ==========================================
# Kill previous instances
pkill -f stock_market_backend.py
pkill -f stock_market_ui.py

echo -e "\033[0;35mIgniting Backend Shadow Engine...\033[0m"
source "$BASE_DIR/jarvis_env/bin/activate"
nohup python3 "$BASE_DIR/stock_market_backend.py" > "$BASE_DIR/backend.log" 2>&1 &

sleep 2
if ! pgrep -f stock_market_backend.py > /dev/null; then
    echo -e "\033[0;31mERROR: Backend failed to ignite. Check backend.log for details.\033[0m"
    cat "$BASE_DIR/backend.log"
    exit 1
fi

# ==========================================
# PHASE 2: THE VISION DEPLOYMENT
# ==========================================
clear
echo -e "\033[0;33m"
cat << 'EOF'
    .-""""""-.
  .'          '.
 /   O      O   \
:                :
|                |
:   \        /   :
 \   '.____.'   /
  '.          .'
    '-......-'
EOF
echo -e "\033[0;36mStock Market Predictor System Initializing...\033[0m"

streamlit run "$BASE_DIR/stock_market_ui.py"
