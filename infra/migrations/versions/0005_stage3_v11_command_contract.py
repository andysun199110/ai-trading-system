"""stage3 v1.1 commercial command execution contract

Revision ID: 0004_stage3_v11
Revises: 0003_stage3
Create Date: 2026-04-25 04:00:00.000000

Changes:
- Add epoch timestamp fields to trading_commands
- Add executed_symbol to trading_execution_reports
- Create position_snapshots table
- Add indexes for efficient querying
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004_stage3_v11'
down_revision = '0003_stage3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to trading_commands
    op.add_column('trading_commands', sa.Column('entry_ref_price', sa.Numeric(precision=10, scale=5), nullable=True))
    op.add_column('trading_commands', sa.Column('max_adverse_move_price', sa.Numeric(precision=10, scale=5), nullable=True))
    op.add_column('trading_commands', sa.Column('created_at_epoch', sa.Integer(), nullable=True))
    op.add_column('trading_commands', sa.Column('expires_at_epoch', sa.Integer(), nullable=True))
    
    # Add index for expires_at_epoch for efficient filtering
    op.create_index('ix_trading_commands_expires_at_epoch', 'trading_commands', ['expires_at_epoch'], unique=False, if_not_exists=True)
    op.create_index('ix_trading_commands_account_server_status', 'trading_commands', ['account_login', 'account_server', 'status', 'expires_at_epoch'], unique=False, if_not_exists=True)
    
    # Add executed_symbol to trading_execution_reports
    op.add_column('trading_execution_reports', sa.Column('executed_symbol', sa.String(length=16), nullable=True))
    
    # Create position_snapshots table
    op.create_table('position_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_login', sa.String(length=32), nullable=False),
        sa.Column('account_server', sa.String(length=64), nullable=False),
        sa.Column('snapshot_time_epoch', sa.Integer(), nullable=False),
        sa.Column('positions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=list),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for position_snapshots
    op.create_index('ix_position_snapshots_account_login', 'position_snapshots', ['account_login'], unique=False, if_not_exists=True)
    op.create_index('ix_position_snapshots_snapshot_time', 'position_snapshots', ['snapshot_time_epoch'], unique=False, if_not_exists=True)
    
    # Populate epoch timestamps for existing records
    op.execute("""
        UPDATE trading_commands 
        SET created_at_epoch = EXTRACT(EPOCH FROM created_at)::INTEGER,
            expires_at_epoch = EXTRACT(EPOCH FROM expires_at)::INTEGER
        WHERE created_at_epoch IS NULL
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_position_snapshots_snapshot_time', table_name='position_snapshots', if_exists=True)
    op.drop_index('ix_position_snapshots_account_login', table_name='position_snapshots', if_exists=True)
    
    op.drop_index('ix_trading_commands_account_server_status', table_name='trading_commands', if_exists=True)
    op.drop_index('ix_trading_commands_expires_at_epoch', table_name='trading_commands', if_exists=True)
    
    # Drop position_snapshots table
    op.drop_table('position_snapshots')
    
    # Remove executed_symbol from trading_execution_reports
    op.drop_column('trading_execution_reports', 'executed_symbol')
    
    # Remove new columns from trading_commands
    op.drop_column('trading_commands', 'expires_at_epoch')
    op.drop_column('trading_commands', 'created_at_epoch')
    op.drop_column('trading_commands', 'max_adverse_move_price')
    op.drop_column('trading_commands', 'entry_ref_price')
