"""stage1 foundation schema"""

from alembic import op
import sqlalchemy as sa

revision = "0001_stage1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("customers", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("email", sa.String(160), nullable=False, unique=True), sa.Column("plan_type", sa.String(32), nullable=False), sa.Column("seat_limit", sa.Integer, nullable=False, server_default="1"), sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")), sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")))
    op.create_table("licenses", sa.Column("id", sa.Integer, primary_key=True), sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id"), nullable=False), sa.Column("license_key", sa.String(128), nullable=False, unique=True), sa.Column("expires_at", sa.DateTime, nullable=False), sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.text("false")), sa.Column("suspended", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.create_table("license_accounts", sa.Column("id", sa.Integer, primary_key=True), sa.Column("license_id", sa.Integer, sa.ForeignKey("licenses.id"), nullable=False), sa.Column("account_login", sa.String(32), nullable=False), sa.Column("account_server", sa.String(64), nullable=False), sa.Column("suspended", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.create_unique_constraint("uq_license_account", "license_accounts", ["license_id", "account_login", "account_server"])
    for t in ["sessions","signals","signal_reviews","risk_decisions","orders","positions","position_actions","event_windows","etf_bias_snapshots","weekly_reviews","optimization_proposals","deployment_records","ea_heartbeats","telegram_events","kill_switch_events","system_health_events","audit_events"]:
        op.create_table(t, sa.Column("id", sa.Integer, primary_key=True), sa.Column("payload", sa.JSON, nullable=True))


def downgrade() -> None:
    for t in ["audit_events","system_health_events","kill_switch_events","telegram_events","ea_heartbeats","deployment_records","optimization_proposals","weekly_reviews","etf_bias_snapshots","event_windows","position_actions","positions","orders","risk_decisions","signal_reviews","signals","sessions","license_accounts","licenses","customers"]:
        op.drop_table(t)
