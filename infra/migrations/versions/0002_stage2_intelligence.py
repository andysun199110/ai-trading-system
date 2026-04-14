"""stage2 intelligence tables"""

from alembic import op
import sqlalchemy as sa

revision = "0002_stage2"
down_revision = "0001_stage1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_invocations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "validation_reports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("validation_reports")
    op.drop_table("ai_invocations")
