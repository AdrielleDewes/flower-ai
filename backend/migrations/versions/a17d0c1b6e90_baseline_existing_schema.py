"""Mark the existing FlowerAI PostgreSQL schema as the Alembic baseline.

Revision ID: a17d0c1b6e90
Revises:
"""

from collections.abc import Sequence

revision: str = "a17d0c1b6e90"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record the existing schema without changing its tables or data."""


def downgrade() -> None:
    """Leave the existing schema intact when removing the baseline marker."""
