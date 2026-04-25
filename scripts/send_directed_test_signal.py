#!/usr/bin/env python3
"""
Minimal one-time test signal injection script for MT5 EA E2E test.
DO NOT USE IN PRODUCTION - for demo testing only.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

# Import models
from services.api_server.models import Signal, Session as AuthSession, EAHeartbeat

# Database URL from env
DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://gold:gold@db:5432/gold_ai")

def get_db_session():
    engine = create_engine(DB_URL)
    return Session(engine)

def identify_target_ea():
    """Identify target demo EA client from heartbeats."""
    db = get_db_session()
    
    # Get recent EA heartbeats
    stmt = select(EAHeartbeat).order_by(EAHeartbeat.heartbeat_at.desc()).limit(10)
    heartbeats = db.execute(stmt).scalars().all()
    
    if not heartbeats:
        print("❌ No EA heartbeats found")
        return None
    
    print(f"✅ Found {len(heartbeats)} EA heartbeat(s)")
    
    # Get the most recent one
    latest = heartbeats[0]
    print(f"   Target account_login: {latest.account_login}")
    print(f"   Last heartbeat: {latest.heartbeat_at}")
    
    # Check if demo account (60082633 is known demo)
    is_demo = "60082633" in latest.account_login or "demo" in latest.account_login.lower()
    print(f"   Demo account: {'✅ YES' if is_demo else '⚠️ UNKNOWN/NO'}")
    
    if not is_demo:
        print("⚠️  WARNING: Account may not be demo. Proceeding with caution.")
    
    return latest.account_login

def create_test_signal(account_login: str, test_id: str, action: str, symbol: str = "XAUUSD", 
                       side: str = "buy", volume: float = 0.01, timeframe: str = "M5"):
    """Create a test signal in the database."""
    db = get_db_session()
    
    signal_id = f"{test_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    payload = {
        "action": action,
        "symbol": symbol,
        "side": side if action == "open" else None,
        "order_type": "market" if action == "open" else None,
        "volume": volume,
        "timeframe": timeframe,
        "source": "manual_test",
        "test_id": test_id,
        "target_account": account_login,
        "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }
    
    signal = Signal(
        signal_id=signal_id,
        symbol=symbol,
        status="new",
        payload=payload
    )
    
    db.add(signal)
    db.commit()
    db.refresh(signal)
    
    print(f"✅ Signal created: {signal_id}")
    print(f"   Action: {action}")
    print(f"   Symbol: {symbol}")
    if action == "open":
        print(f"   Side: {side}, Volume: {volume}")
    print(f"   Target: {account_login}")
    print(f"   Expires: {payload['expires_at']}")
    
    return signal_id

def check_signal_status(signal_id: str):
    """Check signal status."""
    db = get_db_session()
    stmt = select(Signal).where(Signal.signal_id == signal_id)
    signal = db.execute(stmt).scalar_one_or_none()
    
    if signal:
        print(f"📊 Signal status: {signal.status}")
        return signal.status
    else:
        print(f"❌ Signal not found: {signal_id}")
        return None

def main():
    print("=" * 60)
    print("🧪 MT5 EA E2E TEST SIGNAL INJECTION")
    print("=" * 60)
    print()
    
    # Step 1: Identify target EA
    print("📍 Step 1: Identifying target EA...")
    account_login = identify_target_ea()
    
    if not account_login:
        print("❌ FAIL: Could not identify target EA")
        sys.exit(1)
    
    print()
    
    # Step 2: Send OPEN test signal
    print("📤 Step 2: Sending OPEN test signal...")
    open_signal_id = create_test_signal(
        account_login=account_login,
        test_id="TEST-OPEN-20260423-001",
        action="open",
        symbol="XAUUSD",
        side="buy",
        volume=0.01,
        timeframe="M5"
    )
    print()
    
    # Step 3: Wait and check status
    print("⏳ Step 3: Waiting for EA to poll signal (30 seconds)...")
    import time
    time.sleep(30)
    
    print()
    print("📊 Step 4: Checking signal status...")
    status = check_signal_status(open_signal_id)
    print()
    
    # Step 5: Send CLOSE test signal (if open was successful)
    if status in ["acknowledged", "executed", "processing"]:
        print("📤 Step 5: Sending CLOSE test signal...")
        close_signal_id = create_test_signal(
            account_login=account_login,
            test_id="TEST-CLOSE-20260423-002",
            action="close",
            symbol="XAUUSD"
        )
        print()
        
        print("⏳ Step 6: Waiting for EA to process close (30 seconds)...")
        time.sleep(30)
        
        print()
        print("📊 Step 7: Checking close signal status...")
        check_signal_status(close_signal_id)
    else:
        print("⚠️  Skipping CLOSE signal - OPEN not yet acknowledged")
    
    print()
    print("=" * 60)
    print("✅ TEST SIGNAL INJECTION COMPLETE")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Check MT5 container logs for EA execution")
    print("2. Verify orders in MT5 terminal")
    print("3. Check signal status updates in database")
    print()

if __name__ == "__main__":
    main()
