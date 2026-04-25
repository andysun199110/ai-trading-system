#!/usr/bin/env python3
"""
Weekly cleanup job for Commercial Command Execution Contract v1.1.

Runs every Sunday at 03:00 server time to:
- Clean up terminal state commands (executed/failed/expired/rejected/duplicate/cancelled/shadow_skipped/trading_disabled)
- Clean up terminal state execution reports
- Clean up expired sessions
- Does NOT clean up active/available/dispatched or position-related records

Usage:
    python infra/scripts/weekly_cleanup.py
"""

import sys
from datetime import datetime, timedelta

from sqlalchemy import text

from services.api_server.db import get_db


def run_cleanup(dry_run: bool = False) -> dict:
    """
    Run weekly cleanup job.
    
    Args:
        dry_run: If True, only count records without deleting
    
    Returns:
        Dictionary with cleanup statistics
    """
    db = next(get_db())
    stats = {
        "commands_deleted": 0,
        "execution_reports_deleted": 0,
        "sessions_deleted": 0,
        "dry_run": dry_run,
        "started_at": datetime.utcnow().isoformat(),
    }
    
    try:
        # Terminal statuses for cleanup
        terminal_statuses = [
            "EXECUTED", "FAILED", "EXPIRED", "REJECTED",
            "DUPLICATE", "CANCELLED", "SHADOW_SKIPPED", "TRADING_DISABLED"
        ]
        
        # Calculate cutoff (7 days ago)
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        # 1. Clean up terminal state commands older than 7 days
        cmd_stmt = text("""
            DELETE FROM trading_commands
            WHERE status IN :terminal_statuses
            AND executed_at < :cutoff
        """)
        
        if dry_run:
            count_stmt = text("""
                SELECT COUNT(*) FROM trading_commands
                WHERE status IN :terminal_statuses
                AND executed_at < :cutoff
            """)
            result = db.execute(count_stmt, {
                "terminal_statuses": tuple(terminal_statuses),
                "cutoff": cutoff,
            })
            stats["commands_deleted"] = result.scalar()
        else:
            result = db.execute(cmd_stmt, {
                "terminal_statuses": tuple(terminal_statuses),
                "cutoff": cutoff,
            })
            stats["commands_deleted"] = result.rowcount
            db.commit()
        
        # 2. Clean up terminal state execution reports older than 7 days
        report_stmt = text("""
            DELETE FROM trading_execution_reports
            WHERE created_at < :cutoff
            AND command_id IN (
                SELECT command_id FROM trading_commands
                WHERE status IN :terminal_statuses
            )
        """)
        
        if dry_run:
            count_stmt = text("""
                SELECT COUNT(*) FROM trading_execution_reports
                WHERE created_at < :cutoff
                AND command_id IN (
                    SELECT command_id FROM trading_commands
                    WHERE status IN :terminal_statuses
                )
            """)
            result = db.execute(count_stmt, {
                "terminal_statuses": tuple(terminal_statuses),
                "cutoff": cutoff,
            })
            stats["execution_reports_deleted"] = result.scalar()
        else:
            result = db.execute(report_stmt, {
                "terminal_statuses": tuple(terminal_statuses),
                "cutoff": cutoff,
            })
            stats["execution_reports_deleted"] = result.rowcount
            db.commit()
        
        # 3. Clean up expired sessions
        session_stmt = text("""
            DELETE FROM sessions
            WHERE expires_at < :now
        """)
        
        if dry_run:
            count_stmt = text("""
                SELECT COUNT(*) FROM sessions
                WHERE expires_at < :now
            """)
            result = db.execute(count_stmt, {"now": datetime.utcnow()})
            stats["sessions_deleted"] = result.scalar()
        else:
            result = db.execute(session_stmt, {"now": datetime.utcnow()})
            stats["sessions_deleted"] = result.rowcount
            db.commit()
        
        stats["completed_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        db.rollback()
        stats["error"] = str(e)
        stats["completed_at"] = datetime.utcnow().isoformat()
        raise
    finally:
        db.close()
    
    return stats


def main():
    dry_run = "--dry-run" in sys.argv
    
    print(f"Weekly Cleanup Job (v1.1)")
    print(f"Dry run: {dry_run}")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print("-" * 50)
    
    try:
        stats = run_cleanup(dry_run=dry_run)
        
        print(f"Commands deleted: {stats['commands_deleted']}")
        print(f"Execution reports deleted: {stats['execution_reports_deleted']}")
        print(f"Sessions deleted: {stats['sessions_deleted']}")
        print(f"Completed: {stats['completed_at']}")
        
        if stats.get("error"):
            print(f"ERROR: {stats['error']}")
            sys.exit(1)
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
