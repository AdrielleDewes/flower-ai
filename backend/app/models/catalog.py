"""Catalog models for flowers and their descriptive attributes."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Flower(Base):
    """Catalog entry describing a flower available for bouquets."""

    __tablename__ = "flowers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Foliage(Base):
    """Catalog entry describing foliage available for bouquets."""

    __tablename__ = "foliage"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Wrapping(Base):
    """Catalog entry describing bouquet wrapping material."""

    __tablename__ = "wrappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Color(Base):
    """Catalog color that can be associated with flowers."""

    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    hex_code: Mapped[str | None] = mapped_column(String(7), nullable=True)


class Style(Base):
    """Catalog style used to match flowers to bouquet requests."""

    __tablename__ = "styles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Occasion(Base):
    """Catalog occasion used to match flowers to bouquet requests."""

    __tablename__ = "occasions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
