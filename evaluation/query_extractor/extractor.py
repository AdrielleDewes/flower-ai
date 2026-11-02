"""Compatibility exports; the unchanged runtime core lives in the backend."""

from app.services.query_extractor.extractor import (
    QueryExtractor,
)

__all__ = ['QueryExtractor']
