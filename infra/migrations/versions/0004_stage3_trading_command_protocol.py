"""stage3 trading command protocol

Revision ID: 0003_stage3
Revises: 0002_stage2
Create Date: 2026-04-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003_stage3'
down_revision = '0002_stage2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create trading_commands table
    op.create_table('trading_commands',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('command_id', sa.String(length=64), nullable=False),
        sa.Column('account_login', sa.String(length=32), nullable=False),
        sa.Column('account_server', sa.String(length=64), nullable=False),
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('command_type', sa.String(length=32), nullable=False),
        sa.Column('side', sa.String(length=8), nullable=True),
        sa.Column('volume', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('sl', sa.Numeric(precision=10, scale=5), nullable=True),
        sa.Column('tp', sa.Numeric(precision=10, scale=5), nullable=True),
        sa.Column('close_ratio', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('position_ref', sa.String(length=64), nullable=True),
        sa.Column('source_module', sa.String(length=32), nullable=False),
        sa.Column('signal_id', sa.String(length=64), nullable=True),
        sa.Column('strategy_version', sa.String(length=32), nullable=True),
        sa.Column('config_version', sa.String(length=32), nullable=True),
        sa.Column('issued_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, default=100),
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, default='PENDING'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=dict),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for trading_commands
    op.create_index('ix_trading_commands_command_id', 'trading_commands', ['command_id'], unique=True, if_not_exists=True)
    op.create_index('ix_trading_commands_idempotency_key', 'trading_commands', ['idempotency_key'], unique=True, if_not_exists=True)
    op.create_index('ix_trading_commands_account_login', 'trading_commands', ['account_login'], unique=False, if_not_exists=True)
    op.create_index('ix_trading_commands_status', 'trading_commands', ['status'], unique=False, if_not_exists=True)
    op.create_index('ix_trading_commands_signal_id', 'trading_commands', ['signal_id'], unique=False, if_not_exists=True)
    op.create_index('ix_trading_commands_priority_issued', 'trading_commands', ['priority', 'issued_at'], unique=False, if_not_exists=True)
    
    # Create trading_execution_reports table
    op.create_table('trading_execution_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.String(length=64), nullable=False),
        sa.Column('command_id', sa.String(length=64), nullable=False),
        sa.Column('ea_terminal', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('broker_retcode', sa.Integer(), nullable=True),
        sa.Column('broker_comment', sa.Text(), nullable=True),
        sa.Column('executed_price', sa.Numeric(precision=10, scale=5), nullable=True),
        sa.Column('executed_volume', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('sl', sa.Numeric(precision=10, scale=5), nullable=True),
        sa.Column('tp', sa.Numeric(precision=10, scale=5), nullable=True),
        sa.Column('server_time', sa.DateTime(), nullable=True),
        sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for trading_execution_reports
    op.create_index('ix_trading_execution_reports_report_id', 'trading_execution_reports', ['report_id'], unique=True, if_not_exists=True)
    op.create_index('ix_trading_execution_reports_command_id', 'trading_execution_reports', ['command_id'], unique=False, if_not_exists=True)
    
    # Add symbol constraint check (XAUUSD only) - using trigger approach for flexibility
    # Note: PostgreSQL CHECK constraints can't easily reference constants, so we enforce in application logic
    
    # Migrate existing signals to trading_commands (optional - keep signals for backward compat)
    # This is a data migration that can be run separately if needed


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_trading_execution_reports_command_id', table_name='trading_execution_reports', if_exists=True)
    op.drop_index('ix_trading_execution_reports_report_id', table_name='trading_execution_reports', if_exists=True)
    
    op.drop_index('ix_trading_commands_priority_issued', table_name='trading_commands', if_exists=True)
    op.drop_index('ix_trading_commands_signal_id', table_name='trading_commands', if_exists=True)
    op.drop_index('ix_trading_commands_status', table_name='trading_commands', if_exists=True)
    op.drop_index('ix_trading_commands_account_login', table_name='trading_commands', if_exists=True)
    op.drop_index('ix_trading_commands_idempotency_key', table_name='trading_commands', if_exists=True)
    op.drop_index('ix_trading_commands_command_id', table_name='trading_commands', if_exists=True)
    
    # Drop tables
    op.drop_table('trading_execution_reports')
    op.drop_table('trading_commands')
