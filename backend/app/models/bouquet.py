"""Models for saved bouquets and their component items."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Bouquet(Base):
    """A saved bouquet belonging to a florist."""

    __tablename__ = "bouquets"

    id: Mapped[int] = mapped_column(primary_key=True)
    florist_id: Mapped[int] = mapped_column(
        ForeignKey("florists.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )


class BouquetFlower(Base):
    """Flower item and quantity included in a saved bouquet."""

    __tablename__ = "bouquet_flowers"

    bouquet_id: Mapped[int] = mapped_column(
        ForeignKey("bouquets.id"),
        primary_key=True,
    )
    flower_id: Mapped[int] = mapped_column(
        ForeignKey("flowers.id"),
        primary_key=True,
    )
    quantity: Mapped[int] = mapped_column(nullable=False)


class BouquetFoliage(Base):
    """Foliage item and quantity included in a saved bouquet."""

    __tablename__ = "bouquet_foliage"

    bouquet_id: Mapped[int] = mapped_column(
        ForeignKey("bouquets.id"),
        primary_key=True,
    )
    foliage_id: Mapped[int] = mapped_column(
        ForeignKey("foliage.id"),
        primary_key=True,
    )
    quantity: Mapped[int] = mapped_column(nullable=False)


class BouquetWrapping(Base):
    """Wrapping item and quantity included in a saved bouquet."""

    __tablename__ = "bouquet_wrappings"

    bouquet_id: Mapped[int] = mapped_column(
        ForeignKey("bouquets.id"),
        primary_key=True,
    )
    wrapping_id: Mapped[int] = mapped_column(
        ForeignKey("wrappings.id"),
        primary_key=True,
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
