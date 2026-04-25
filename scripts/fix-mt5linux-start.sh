#!/bin/bash
# Fix Wine prefix ownership
chown -R abc:abc /config/.wine 2>/dev/null || true
echo "Wine prefix ownership fixed"

# Force rpyc 5.2.3 for mt5linux compatibility (before start.sh runs)
pip3 install --break-system-packages --force-reinstall "rpyc==5.2.3" 2>&1 | tail -3
echo "rpyc forced to 5.2.3"

# Configure MT5 login credentials (after start.sh patches)
cat > /tmp/config-mt5-login.py << 'PYEOF'
import os
import configparser
from pathlib import Path

login = os.environ.get('MT5_LOGIN', '')
password = os.environ.get('MT5_PASSWORD', '')
server = os.environ.get('MT5_SERVER', '')

if not login or not password or not server:
    print("[MT5] No credentials provided, skipping auto-login")
    exit(0)

print(f"[MT5] Configuring login: {login}@{server}")

# Find MT5 terminal directory
terminals_dir = Path('/config/.wine/drive_c/users/abc/AppData/Roaming/MetaQuotes/Terminal')
if not terminals_dir.exists():
    print("[MT5] Terminal directory not found")
    exit(0)

terminal_id = next(terminals_dir.iterdir(), None)
if not terminal_id:
    print("[MT5] No terminal ID found")
    exit(0)

config_dir = terminal_id / 'config'
config_dir.mkdir(parents=True, exist_ok=True)

# Create accounts.ini
config = configparser.ConfigParser()
config[f'Account_{login}'] = {
    'login': login,
    'password': password,
    'server': server,
    'save_password': '1'
}

accounts_file = config_dir / 'accounts.ini'
with open(accounts_file, 'w') as f:
    config.write(f)

print(f"[MT5] accounts.ini created at {accounts_file}")

# Set ownership
os.system(f'chown -R abc:abc {config_dir}')
PYEOF

python3 /tmp/config-mt5-login.py 2>&1

# Also configure server.ini with actual IP address
cat > /tmp/config-mt5-server.py << 'PYEOF'
import os
from pathlib import Path

server_name = os.environ.get('MT5_SERVER', 'TradeMaxGlobal-Demo')
server_addr = os.environ.get('MT5_SERVER_ADDRESS', '34.77.56.111:443')

terminals_dir = Path('/config/.wine/drive_c/users/abc/AppData/Roaming/MetaQuotes/Terminal')
if not terminals_dir.exists():
    print("[MT5 Server] Terminal directory not found")
    exit(0)

# Use Community terminal
terminal_id = terminals_dir / 'Community'
terminal_id.mkdir(parents=True, exist_ok=True)
config_dir = terminal_id / 'config'
config_dir.mkdir(parents=True, exist_ok=True)

server_file = config_dir / 'server.ini'
with open(server_file, 'w') as f:
    f.write(f'[{server_name}]\n')
    f.write(f'server_name={server_name}\n')
    f.write(f'server_owner=TradeMax Global\n')
    f.write(f'server_address={server_addr}\n')
    f.write('server_demo=1\n')
    f.write('server_auto_disable=0\n')

print(f"[MT5 Server] server.ini created at {server_file}")
os.system(f'chown -R abc:abc {config_dir}')
PYEOF

python3 /tmp/config-mt5-server.py 2>&1
echo "MT5 configuration complete"

# Patch the start.sh to use rpyc 5.2.3 and remove unsupported -w flag
cat > /tmp/patch_start.py << 'PYEOF'
with open('/Metatrader/start.sh', 'r') as f:
    content = f.read()

# Add rpyc fix before mt5linux start
lines = content.split('\n')
new_lines = []
for line in lines:
    if '[7/7] Starting the mt5linux server' in line:
        new_lines.append('# Force rpyc 5.2.3 before starting mt5linux')
        new_lines.append('pip3 install --break-system-packages --force-reinstall "rpyc==5.2.3" 2>/dev/null || true')
    # Remove -w flag
    line = line.replace('-w $wine_executable python.exe', '')
    new_lines.append(line)

with open('/Metatrader/start.sh', 'w') as f:
    f.write('\n'.join(new_lines))

print("Start script patched")
PYEOF

python3 /tmp/patch_start.py 2>/dev/null || true
echo "mt5linux start script patched"
