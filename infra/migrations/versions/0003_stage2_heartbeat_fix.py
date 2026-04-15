"""stage2 heartbeat table fix

Revision ID: 0003_stage2
Revises: 0002_stage2
Create Date: 2026-04-15 13:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0003_stage2'
down_revision = '0002_stage2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add account_login column to ea_heartbeats
    op.add_column('ea_heartbeats', sa.Column('account_login', sa.String(32), nullable=True))
    op.add_column('ea_heartbeats', sa.Column('heartbeat_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Set not null after populating
    op.alter_column('ea_heartbeats', 'account_login', existing_type=sa.String(32), nullable=False)
    op.alter_column('ea_heartbeats', 'heartbeat_at', existing_type=sa.DateTime(), nullable=False)
    
    # Add index for faster lookups
    op.create_index('ix_ea_heartbeats_account_login', 'ea_heartbeats', ['account_login'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ea_heartbeats_account_login', table_name='ea_heartbeats')
    op.drop_column('ea_heartbeats', 'heartbeat_at')
    op.drop_column('ea_heartbeats', 'account_login')
