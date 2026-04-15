"""stage2 schema indexes and constraints

Revision ID: 0002_stage2
Revises: 0001_stage1
Create Date: 2026-04-15 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0002_stage2'
down_revision = '0001_stage1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add performance indexes
    op.create_index('ix_audit_events_event_type', 'audit_events', ['event_type'], unique=False, if_not_exists=True)
    op.create_index('ix_audit_events_created_at', 'audit_events', ['created_at'], unique=False, if_not_exists=True)
    op.create_index('ix_sessions_license_id', 'sessions', ['license_id'], unique=False, if_not_exists=True)
    op.create_index('ix_sessions_account_login', 'sessions', ['account_login'], unique=False, if_not_exists=True)
    op.create_index('ix_license_accounts_license_id', 'license_accounts', ['license_id'], unique=False, if_not_exists=True)
    op.create_index('ix_licenses_customer_id', 'licenses', ['customer_id'], unique=False, if_not_exists=True)


def downgrade() -> None:
    op.drop_index('ix_licenses_customer_id', table_name='licenses', if_exists=True)
    op.drop_index('ix_license_accounts_license_id', table_name='license_accounts', if_exists=True)
    op.drop_index('ix_sessions_account_login', table_name='sessions', if_exists=True)
    op.drop_index('ix_sessions_license_id', table_name='sessions', if_exists=True)
    op.drop_index('ix_audit_events_created_at', table_name='audit_events', if_exists=True)
    op.drop_index('ix_audit_events_event_type', table_name='audit_events', if_exists=True)
