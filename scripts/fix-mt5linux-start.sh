#!/bin/bash
# Fix Wine prefix ownership
chown -R abc:abc /config/.wine 2>/dev/null || true
echo "Wine prefix ownership fixed"

# Patch the start script to use rpyc 5.2.3
cat > /tmp/patch_rpyc.py << 'PYEOF'
import re
with open('/Metatrader/start.sh', 'r') as f:
    content = f.read()

# Add rpyc version fix before mt5linux start
old_pattern = r'(\[7/7\] Starting the mt5linux server\.\.\.)'
new_replacement = '''# Fix rpyc version before starting mt5linux
pip3 install --break-system-packages "rpyc==5.2.3" 2>/dev/null || true
echo "rpyc version fixed"

\1'''

content = re.sub(old_pattern, new_replacement, content)

# Remove -w flag
content = content.replace('-w $wine_executable python.exe', '')

with open('/Metatrader/start.sh', 'w') as f:
    f.write(content)

print("Start script patched")
PYEOF

python3 /tmp/patch_rpyc.py 2>/dev/null || true
echo "Start script patching complete"
