"""Florist models and florist-specific catalog offerings."""

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Florist(Base):
    """A florist that offers catalog items at its own prices."""

    __tablename__ = "florists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)


class FloristFlower(Base):
    """A flower offered by a florist, with its price and active status."""

    __tablename__ = "florist_flowers"

    florist_id: Mapped[int] = mapped_column(
        ForeignKey("florists.id"),
        primary_key=True,
    )
    flower_id: Mapped[int] = mapped_column(
        ForeignKey("flowers.id"),
        primary_key=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class FloristFoliage(Base):
    """Foliage offered by a florist, with its price and active status."""

    __tablename__ = "florist_foliage"

    florist_id: Mapped[int] = mapped_column(
        ForeignKey("florists.id"),
        primary_key=True,
    )
    foliage_id: Mapped[int] = mapped_column(
        ForeignKey("foliage.id"),
        primary_key=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class FloristWrapping(Base):
    """Wrapping offered by a florist, with its price and active status."""

    __tablename__ = "florist_wrappings"

    florist_id: Mapped[int] = mapped_column(
        ForeignKey("florists.id"),
        primary_key=True,
    )
    wrapping_id: Mapped[int] = mapped_column(
        ForeignKey("wrappings.id"),
        primary_key=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
