#!/bin/bash
# Fix Wine prefix ownership
chown -R abc:abc /config/.wine 2>/dev/null || true
echo "Wine prefix ownership fixed"

# Force rpyc 5.2.3 for mt5linux compatibility (before start.sh runs)
pip3 install --break-system-packages --force-reinstall "rpyc==5.2.3" 2>&1 | tail -3
echo "rpyc forced to 5.2.3"

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
