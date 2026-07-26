#!/bin/bash

BASE_DIR="$(pwd)"

# ==========================================
# PHASE 0: ZERO-FRICTION SETUP
# ==========================================
echo -e "\033[0;36mInitializing Zero-Friction Setup...\033[0m"

# Install system dependencies if missing
check_and_install_sys_deps() {
    local missing=0
    for cmd in python3 pip; do
        if ! command -v $cmd &> /dev/null; then
            echo -e "\033[0;33m$cmd is missing.\033[0m"
            missing=1
        fi
    done
    
    if ! python3 -m venv --help &> /dev/null; then
        echo -e "\033[0;33mpython3-venv is missing.\033[0m"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        echo -e "\033[0;33mAttempting to install missing system dependencies...\033[0m"
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv build-essential
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3 python3-pip gcc gcc-c++
        elif command -v pacman &> /dev/null; then
            sudo pacman -Sy --noconfirm python python-pip base-devel
        else
            echo -e "\033[0;31mCould not detect package manager. Please install python3, pip, and python3-venv manually.\033[0m"
            exit 1
        fi
    fi
}

check_and_install_sys_deps

if [ ! -d "$BASE_DIR/jarvis_env" ]; then
    echo -e "\033[0;33mVirtual Environment missing. Creating one now...\033[0m"
    python3 -m venv "$BASE_DIR/jarvis_env"
    
    echo -e "\033[0;33mInstalling AI & UI dependencies (this may take a minute)...\033[0m"
    source "$BASE_DIR/jarvis_env/bin/activate"
    pip install --upgrade pip
    
    req_file="$BASE_DIR/requirements.txt"
    echo -e "\033[0;36mInstalling from $req_file...\033[0m"
    if pip install -r "$req_file"; then
        echo -e "\033[0;32mRequirements installed successfully.\033[0m"
    else
        echo -e "\033[0;33mPrimary installation failed. Attempting redundancy methods...\033[0m"
        # Redundancy 1: No cache
        if pip install -r "$req_file" --no-cache-dir; then
            echo -e "\033[0;32mRequirements installed successfully using --no-cache-dir.\033[0m"
        # Redundancy 2: Prefer binary
        elif pip install -r "$req_file" --prefer-binary; then
            echo -e "\033[0;32mRequirements installed successfully using --prefer-binary.\033[0m"
        # Redundancy 3: Try different mirror
        elif pip install -r "$req_file" -i https://pypi.python.org/simple/; then
            echo -e "\033[0;32mRequirements installed successfully using alternate mirror.\033[0m"
        else
            echo -e "\033[0;31mCRITICAL ERROR: Failed to install requirements after all redundancy attempts. The application might be unstable.\033[0m"
        fi
    fi
    
    deactivate
    echo -e "\033[0;32mEnvironment setup complete!\033[0m"
fi

if [ ! -f "$BASE_DIR/assets.json" ]; then
    echo "oooi you dont need money news huhhh??"
fi

# ==========================================
# PHASE 1: BACKEND IGNITION
# ==========================================
# Kill previous instances
pkill -f stock_market_backend.py
pkill -f stock_market_ui.py
pkill -f uvicorn

# Remove old ready flag to force UI to wait for fresh data
rm -f "$BASE_DIR/data_lake/.ready"

echo -e "\033[0;35mIgniting Backend Shadow Engine & API Server...\033[0m"
nohup "$BASE_DIR/jarvis_env/bin/python" "$BASE_DIR/stock_market_backend.py" > "$BASE_DIR/backend.log" 2>&1 &
nohup "$BASE_DIR/jarvis_env/bin/uvicorn" api_server:app --host 0.0.0.0 --port 8000 > "$BASE_DIR/api.log" 2>&1 &

sleep 2
if ! pgrep -f stock_market_backend.py > /dev/null; then
    echo -e "\033[0;31mERROR: Backend failed to ignite. Check backend.log for details.\033[0m"
    cat "$BASE_DIR/backend.log"
    exit 1
fi

# ==========================================
# PHASE 2: DATA SYNCHRONIZATION
# ==========================================
echo -e "\033[0;36mWaiting for initial data sync to complete before starting UI...\033[0m"

while [ ! -f "$BASE_DIR/data_lake/.ready" ]; do
    if ! pgrep -f stock_market_backend.py > /dev/null; then
        echo -e "\n\033[0;31mCRITICAL ERROR: Backend process died during sync. Check backend.log.\033[0m"
        exit 1
    fi
    sleep 5
    echo -n "."
done
echo -e "\n\033[0;32mData Sync Complete!\033[0m"

# ==========================================
# PHASE 3: THE VISION DEPLOYMENT
# ==========================================
clear

echo -e "\033[0;36mStock Market Predictor System Initializing...\033[0m"

"$BASE_DIR/jarvis_env/bin/streamlit" run "$BASE_DIR/stock_market_ui.py"
