from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FlowerInventory(Base):
    __tablename__ = "flower_inventory"

    florist_id: Mapped[int] = mapped_column(
        ForeignKey("florists.id"),
        primary_key=True,
    )
    flower_id: Mapped[int] = mapped_column(
        ForeignKey("flowers.id"),
        primary_key=True,
    )
    quantity: Mapped[int] = mapped_column(nullable=False, default=0)


class FoliageInventory(Base):
    __tablename__ = "foliage_inventory"

    florist_id: Mapped[int] = mapped_column(
        ForeignKey("florists.id"),
        primary_key=True,
    )
    foliage_id: Mapped[int] = mapped_column(
        ForeignKey("foliage.id"),
        primary_key=True,
    )
    quantity: Mapped[int] = mapped_column(nullable=False, default=0)


class WrappingInventory(Base):
    __tablename__ = "wrapping_inventory"

    florist_id: Mapped[int] = mapped_column(
        ForeignKey("florists.id"),
        primary_key=True,
    )
    wrapping_id: Mapped[int] = mapped_column(
        ForeignKey("wrappings.id"),
        primary_key=True,
    )
    quantity: Mapped[int] = mapped_column(nullable=False, default=0)