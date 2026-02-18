#!/bin/bash

# ==========================================
# PHASE 1: OLLAMA BRAIN WAKEUP
# ==========================================
pgrep ollama > /dev/null || (ollama serve > /dev/null 2>&1 & sleep 5)

# ==========================================
# PHASE 2: SHADOW IGNITION (BACKEND - NO PASSWORD)
# ==========================================
tmux kill-session -t jarvis_backend 2>/dev/null
# FIXED: Path now correctly points inside JARVIS_System
tmux new-session -d -s jarvis_backend "bash -c 'source /home/dxt/JARVIS_System/jarvis_env/bin/activate && python3 /home/dxt/JARVIS_System/jarvis_backend.py'"

echo -e "\033[0;35mChecking Shadow Engine Heartbeat...\033[0m"
sleep 2
if ! tmux has-session -t jarvis_backend 2>/dev/null; then
    echo -e "\033[0;31mERROR: Backend failed to ignite. Check environment paths.\033[0m"
    exit 1
fi

# ==========================================
# PHASE 3: FRONTEND SECURITY GATE
# ==========================================
clear
echo -e "\033[0;36mGood morning, Boss. Sovereign Engine V6.1 is active in the shadows.\033[0m"
read -p "Initiate Jarvis Vision Interface? [Y/n]: " init_ans
if [[ "$init_ans" != "Y" && "$init_ans" != "y" && "$init_ans" != "" ]]; then exit 0; fi

echo ""
read -s -p "Enter Authorization Code: " passwd
echo ""

if [[ "$passwd" != "stark" ]]; then
    echo -e "\033[0;31mAUTHORIZATION FAILED. INTRUSION LOGGED.\033[0m"
    exit 1
fi

# ==========================================
# PHASE 4: THE VISION DEPLOYMENT
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
echo -e "\033[0;36mAUTHORIZATION ACCEPTED. WELCOME BACK.\033[0m"

tmux kill-session -t sovereign_ui 2>/dev/null
# FIXED: Path now correctly points inside JARVIS_System
tmux new-session -d -s sovereign_ui "bash -c 'source /home/dxt/JARVIS_System/jarvis_env/bin/activate && streamlit run /home/dxt/JARVIS_System/jarvis_ui.py'"

tmux attach -t sovereign_ui#!/bin/bash

# ==========================================
# PHASE 1: OLLAMA BRAIN WAKEUP
# ==========================================
pgrep ollama > /dev/null || (ollama serve > /dev/null 2>&1 & sleep 5)

# ==========================================
# PHASE 2: SHADOW IGNITION (BACKEND - NO PASSWORD)
# ==========================================
tmux kill-session -t jarvis_backend 2>/dev/null
# FIXED: Path now correctly points inside JARVIS_System
tmux new-session -d -s jarvis_backend "bash -c 'source /home/dxt/JARVIS_System/jarvis_env/bin/activate && python3 /home/dxt/JARVIS_System/jarvis_backend.py'"

echo -e "\033[0;35mChecking Shadow Engine Heartbeat...\033[0m"
sleep 2
if ! tmux has-session -t jarvis_backend 2>/dev/null; then
    echo -e "\033[0;31mERROR: Backend failed to ignite. Check environment paths.\033[0m"
    exit 1
fi

# ==========================================
# PHASE 3: FRONTEND SECURITY GATE
# ==========================================
clear
echo -e "\033[0;36mGood morning, Boss. Sovereign Engine V6.1 is active in the shadows.\033[0m"
read -p "Initiate Jarvis Vision Interface? [Y/n]: " init_ans
if [[ "$init_ans" != "Y" && "$init_ans" != "y" && "$init_ans" != "" ]]; then exit 0; fi

echo ""
read -s -p "Enter Authorization Code: " passwd
echo ""

if [[ "$passwd" != "stark" ]]; then
    echo -e "\033[0;31mAUTHORIZATION FAILED. INTRUSION LOGGED.\033[0m"
    exit 1
fi

# ==========================================
# PHASE 4: THE VISION DEPLOYMENT
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
echo -e "\033[0;36mAUTHORIZATION ACCEPTED. WELCOME BACK.\033[0m"

tmux kill-session -t sovereign_ui 2>/dev/null
# FIXED: Path now correctly points inside JARVIS_System
tmux new-session -d -s sovereign_ui "bash -c 'source /home/dxt/JARVIS_System/jarvis_env/bin/activate && streamlit run /home/dxt/JARVIS_System/jarvis_ui.py'"

tmux attach -t sovereign_ui
