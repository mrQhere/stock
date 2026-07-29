#!/bin/bash
set -e

echo -e "\033[0;36m╔══════════════════════════════════════════════════════════╗\033[0m"
echo -e "\033[0;36m║               Credential Reset Utility                   ║\033[0m"
echo -e "\033[0;36m╚══════════════════════════════════════════════════════════╝\033[0m"
echo ""

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="$BASE_DIR/.streamlit/secrets.toml"
BASHRC_FILE="$HOME/.bashrc"

# Generate random secure strings
NEW_PASS=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 16)
NEW_API_KEY="sk-quant-$(tr -dc A-Za-z0-9 </dev/urandom | head -c 12)"

# 1. Update UI Password
mkdir -p "$BASE_DIR/.streamlit"
echo "APP_PASSWORD = \"$NEW_PASS\"" > "$SECRETS_FILE"
echo -e "\033[0;32m[✓] Generated new Dashboard Password.\033[0m"

# 2. Update API Key in bashrc
# Remove existing key
if grep -q "export QUANT_API_KEY=" "$BASHRC_FILE"; then
    sed -i '/export QUANT_API_KEY=/d' "$BASHRC_FILE"
fi
echo "export QUANT_API_KEY=\"$NEW_API_KEY\"" >> "$BASHRC_FILE"
echo -e "\033[0;32m[✓] Generated new REST API Key and saved to ~/.bashrc.\033[0m"

echo ""
echo -e "\033[0;33mIMPORTANT: Please copy these down and restart your terminal!\033[0m"
echo -e "Dashboard Password : \033[1;36m$NEW_PASS\033[0m"
echo -e "REST API Key       : \033[1;36m$NEW_API_KEY\033[0m"
echo ""
echo "Note: If the system is currently running, please restart it for the new credentials to take effect."
echo "You can stop it with: pkill -f stock_market_backend && pkill -f uvicorn"
