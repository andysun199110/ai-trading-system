#!/usr/bin/env bash
set -uo pipefail

# Stage 2 Verification Script
cd "$(dirname "$0")/../.."

PASS=0
FAIL=0

check() {
    local name="$1"
    local cmd="$2"
    
    echo -n "Checking: $name ... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo "PASS"
        PASS=$((PASS + 1))
        return 0
    else
        echo "FAIL"
        FAIL=$((FAIL + 1))
        return 0
    fi
}

echo "============================================================"
echo "Stage 2 Verification"
echo "============================================================"
echo ""

# 1. Docker Compose Status
echo "--- Container Status ---"
check "API container running" "docker compose ps | grep -q 'ai-trading-api.*Up'"
check "DB container running" "docker compose ps | grep -q 'ai-trading-db.*Up'"
check "Redis container running" "docker compose ps | grep -q 'ai-trading-redis.*Up'"
check "Nginx container running" "docker compose ps | grep -q 'ai-trading-nginx.*Up'"
echo ""

# 2. Database Migration
echo "--- Database Migration ---"
check "Alembic migration current" "docker compose exec -T api alembic -c infra/migrations/alembic.ini current 2>&1 | grep -qE '000[23]_stage2'"
echo ""

# 3. Health Endpoints
echo "--- Health Endpoints ---"
check "Root health endpoint" "curl -fsS http://127.0.0.1/health >/dev/null"
check "Admin health endpoint" "curl -fsS http://127.0.0.1/admin/health >/dev/null"
echo ""

# 4. Activation Integration Test
echo "--- Activation Integration Test ---"
ACTIVATE_RESULT=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/activate \
    -H "Content-Type: application/json" \
    -d '{"license_key":"MT5-LIVE-SG","account_login":"60066926","account_server":"TradeMaxGlobal-Demo"}')

if echo "$ACTIVATE_RESULT" | grep -q '"token"'; then
    echo "Activation test: PASS (token received)"
    PASS=$((PASS + 1))
else
    echo "Activation test: FAIL"
    echo "Response: $ACTIVATE_RESULT"
    FAIL=$((FAIL + 1))
fi
echo ""

# 5. API Log Check
echo "--- API Log Check (last 200 lines) ---"
if docker compose logs api --tail 200 2>&1 | grep -q "column does not exist"; then
    echo "Found 'column does not exist' errors: FAIL"
    FAIL=$((FAIL + 1))
else
    echo "No 'column does not exist' errors: PASS"
    PASS=$((PASS + 1))
fi
echo ""

# Summary
echo "============================================================"
echo "Summary"
echo "============================================================"
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✓ Stage 2 verification complete!"
    exit 0
else
    echo "✗ Stage 2 verification failed with $FAIL error(s)"
    exit 1
fi
