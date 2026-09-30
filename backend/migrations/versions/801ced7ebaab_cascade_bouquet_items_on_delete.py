"""Add cascade deletes to bouquet composition foreign keys.

Revision ID: 801ced7ebaab
Revises: a17d0c1b6e90
"""

from collections.abc import Sequence

from alembic import op

revision: str = "801ced7ebaab"
down_revision: str | Sequence[str] | None = "a17d0c1b6e90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Recreate bouquet item foreign keys with cascade deletes."""
    op.drop_constraint(
        "bouquet_flowers_bouquet_id_fkey",
        "bouquet_flowers",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "bouquet_flowers_bouquet_id_fkey",
        "bouquet_flowers",
        "bouquets",
        ["bouquet_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "bouquet_foliage_bouquet_id_fkey",
        "bouquet_foliage",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "bouquet_foliage_bouquet_id_fkey",
        "bouquet_foliage",
        "bouquets",
        ["bouquet_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "bouquet_wrappings_bouquet_id_fkey",
        "bouquet_wrappings",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "bouquet_wrappings_bouquet_id_fkey",
        "bouquet_wrappings",
        "bouquets",
        ["bouquet_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Restore the previous foreign keys without cascade deletes."""
    op.drop_constraint(
        "bouquet_wrappings_bouquet_id_fkey",
        "bouquet_wrappings",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "bouquet_wrappings_bouquet_id_fkey",
        "bouquet_wrappings",
        "bouquets",
        ["bouquet_id"],
        ["id"],
    )

    op.drop_constraint(
        "bouquet_foliage_bouquet_id_fkey",
        "bouquet_foliage",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "bouquet_foliage_bouquet_id_fkey",
        "bouquet_foliage",
        "bouquets",
        ["bouquet_id"],
        ["id"],
    )

    op.drop_constraint(
        "bouquet_flowers_bouquet_id_fkey",
        "bouquet_flowers",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "bouquet_flowers_bouquet_id_fkey",
        "bouquet_flowers",
        "bouquets",
        ["bouquet_id"],
        ["id"],
    )
