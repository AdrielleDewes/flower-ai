"""Association models connecting flowers to colors, styles, and occasions."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FlowerColor(Base):
    """Association linking a flower to one of its available colors."""

    __tablename__ = "flower_colors"

    flower_id: Mapped[int] = mapped_column(
        ForeignKey("flowers.id"),
        primary_key=True,
    )
    color_id: Mapped[int] = mapped_column(
        ForeignKey("colors.id"),
        primary_key=True,
    )


class FlowerStyle(Base):
    """Association linking a flower to a bouquet style."""

    __tablename__ = "flower_styles"

    flower_id: Mapped[int] = mapped_column(
        ForeignKey("flowers.id"),
        primary_key=True,
    )
    style_id: Mapped[int] = mapped_column(
        ForeignKey("styles.id"),
        primary_key=True,
    )


class FlowerOccasion(Base):
    """Association linking a flower to a suitable occasion."""

    __tablename__ = "flower_occasions"

    flower_id: Mapped[int] = mapped_column(
        ForeignKey("flowers.id"),
        primary_key=True,
    )
    occasion_id: Mapped[int] = mapped_column(
        ForeignKey("occasions.id"),
        primary_key=True,
    )
