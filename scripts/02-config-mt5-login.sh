#!/bin/bash
# Configure MT5 login credentials
set -e

LOGIN="${MT5_LOGIN:-}"
PASSWORD="${MT5_PASSWORD:-}"
SERVER="${MT5_SERVER:-}"

if [ -z "$LOGIN" ] || [ -z "$PASSWORD" ] || [ -z "$SERVER" ]; then
    echo "[MT5] No credentials provided, skipping auto-login config"
    exit 0
fi

echo "[MT5] Configuring login: $LOGIN@$SERVER"

# Find the MT5 terminal directory
MT5_DIR="/config/.wine/drive_c/users/abc/AppData/Roaming/MetaQuotes/Terminal"
if [ ! -d "$MT5_DIR" ]; then
    echo "[MT5] Terminal directory not found, waiting..."
    sleep 5
fi

# Get the first terminal ID
TERMINAL_ID=$(ls -1 "$MT5_DIR" 2>/dev/null | head -1)
if [ -z "$TERMINAL_ID" ]; then
    echo "[MT5] No terminal ID found"
    exit 0
fi

CONFIG_DIR="$MT5_DIR/$TERMINAL_ID/config"
mkdir -p "$CONFIG_DIR"

# Create accounts.ini with credentials
cat > "$CONFIG_DIR/accounts.ini" << INIEOF
[Account_${LOGIN}]
login=${LOGIN}
password=${PASSWORD}
server=${SERVER}
save_password=1
INIEOF

echo "[MT5] accounts.ini created"
chown -R abc:abc "$CONFIG_DIR"
