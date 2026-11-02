"""Compatibility exports; the unchanged runtime core lives in the backend."""

from app.services.query_extractor.vocabulary import (
    ALIASES,
    CatalogMatcher,
    FlowerMention,
)

__all__ = ['ALIASES', 'CatalogMatcher', 'FlowerMention']
