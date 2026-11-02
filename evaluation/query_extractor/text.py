"""Compatibility exports; the unchanged runtime core lives in the backend."""

from app.services.query_extractor.text import (
    Clause,
    Token,
    clauses,
    normalize,
    tokens,
)

__all__ = ['Clause', 'Token', 'clauses', 'normalize', 'tokens']
