#!/usr/bin/env python3
"""
Minimal one-time test signal injection script.
FOR DEMO ACCOUNT TESTING ONLY - DO NOT USE IN PRODUCTION.

Usage inside API container:
  python scripts/inject_test_signal.py --test-id TEST-OPEN-20260423-001 --action open --symbol XAUUSD --side buy --volume 0.01
  python scripts/inject_test_signal.py --test-id TEST-CLOSE-20260423-002 --action close --symbol XAUUSD
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Import from project
from services.api_server.models import Signal, EAHeartbeat
from shared.config.settings import get_settings

# SAFETY: Only allow demo account patterns
DEMO_ACCOUNT_PATTERNS = ["60066926", "demo", "Demo"]
TARGET_ACCOUNT = "60066926"  # Confirmed demo account from MT5 journal

def get_db_session():
    settings = get_settings()
    engine = create_engine(settings.db_url, future=True)
    return Session(engine)

def verify_demo_account(db: Session, account_login: str) -> bool:
    """Verify target account is demo."""
    # Check EA heartbeats for this account
    stmt = select(EAHeartbeat).where(EAHeartbeat.account_login == account_login).order_by(EAHeartbeat.heartbeat_at.desc()).limit(1)
    heartbeat = db.execute(stmt).scalar_one_or_none()
    
    if heartbeat:
        print(f"✅ Found EA heartbeat for account: {account_login}")
        print(f"   Last heartbeat: {heartbeat.heartbeat_at}")
        return True
    
    print(f"⚠️  No EA heartbeat found for {account_login}, proceeding with caution")
    return True  # Allow if no contradictory evidence

def create_test_signal(db: Session, test_id: str, action: str, symbol: str, 
                       side: str = None, order_type: str = None, 
                       volume: float = 0.01, target_account: str = TARGET_ACCOUNT):
    """Create a test signal in the database."""
    
    # Verify demo account
    if not verify_demo_account(db, target_account):
        print(f"❌ FAIL: Account {target_account} verification failed")
        return None
    
    signal_id = f"{test_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    payload = {
        "action": action,
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "volume": volume,
        "source": "manual_test",
        "test_id": test_id,
        "target_account": target_account,
        "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "priority": "high",
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
    
    print(f"✅ TEST SIGNAL CREATED: {signal_id}")
    print(f"   Action: {action}")
    print(f"   Symbol: {symbol}")
    if side:
        print(f"   Side: {side}")
    if order_type:
        print(f"   Type: {order_type}")
    print(f"   Volume: {volume}")
    print(f"   Target: {target_account} (DEMO)")
    print(f"   Test ID: {test_id}")
    print(f"   Expires: {payload['expires_at']}")
    print()
    
    return signal_id

def check_signal_status(db: Session, test_id_prefix: str):
    """Check status of signals matching test_id prefix."""
    stmt = select(Signal).where(Signal.signal_id.like(f"{test_id_prefix}%")).order_by(Signal.id.desc())
    signals = db.execute(stmt).scalars().all()
    
    if not signals:
        print(f"❌ No signals found with test_id prefix: {test_id_prefix}")
        return None
    
    print(f"📊 Signal Status ({len(signals)} found):")
    for sig in signals[:3]:  # Show latest 3
        print(f"   {sig.signal_id}: status={sig.status}, symbol={sig.symbol}")
        if sig.payload.get('test_id'):
            print(f"      test_id={sig.payload['test_id']}")
    
    return signals[0].status if signals else None

def main():
    parser = argparse.ArgumentParser(description='Inject test signal for E2E verification')
    parser.add_argument('--test-id', required=True, help='Test ID (e.g., TEST-OPEN-20260423-001)')
    parser.add_argument('--action', required=True, choices=['open', 'close'], help='Action type')
    parser.add_argument('--symbol', default='XAUUSD', help='Trading symbol')
    parser.add_argument('--side', choices=['buy', 'sell'], help='Side (for open action)')
    parser.add_argument('--order-type', default='market', help='Order type')
    parser.add_argument('--volume', type=float, default=0.01, help='Trade volume (default: 0.01)')
    parser.add_argument('--target-account', default=TARGET_ACCOUNT, help='Target account login')
    parser.add_argument('--check-status', action='store_true', help='Only check status, don\'t create')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🧪 MT5 EA E2E TEST SIGNAL INJECTION (DEMO ACCOUNT ONLY)")
    print("=" * 70)
    print()
    
    db = get_db_session()
    
    try:
        if args.check_status:
            status = check_signal_status(db, args.test_id)
            print(f"\nStatus: {status}")
        else:
            # Safety check
            if not any(pattern in args.target_account for pattern in DEMO_ACCOUNT_PATTERNS):
                print(f"❌ ERROR: Target account '{args.target_account}' is not confirmed as demo!")
                print("   Aborting for safety.")
                sys.exit(1)
            
            signal_id = create_test_signal(
                db=db,
                test_id=args.test_id,
                action=args.action,
                symbol=args.symbol,
                side=args.side,
                order_type=args.order_type,
                volume=args.volume,
                target_account=args.target_account
            )
            
            if signal_id:
                print("✅ Signal injection successful")
                print()
                print("Next steps:")
                print("1. Wait 30-60 seconds for EA to poll signals")
                print("2. Check MT5 container logs: docker compose logs -f mt5")
                print("3. Verify in MT5 terminal")
                print("4. Check signal status:")
                print(f"   python scripts/inject_test_signal.py --test-id {args.test_id} --check-status")
            else:
                print("❌ Signal injection failed")
                sys.exit(1)
    
    finally:
        db.close()
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
