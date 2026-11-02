"""Reusable FastAPI dependencies."""

import logging
from dataclasses import replace

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import OllamaConfig
from app.database import get_db
from app.models.florist import Florist
from app.services.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


def get_interpretation_provider() -> OllamaProvider:
    """Create a request-local provider; configuration errors do not break manual entry."""
    try:
        config = OllamaConfig.from_env()
        if config.model != "qwen3:1.7b" or config.think is True:
            raise ValueError("The POC requires qwen3:1.7b with think:false.")
        return OllamaProvider(replace(config, think=False))
    except ValueError as exc:
        logger.warning("Interpretation provider configuration is unavailable")
        raise HTTPException(status_code=503, detail="Interpretation service is not configured.") from exc


def get_florist(
    florist_id: int,
    db: Session = Depends(get_db),  # noqa: B008
) -> Florist:
    """Return a florist or raise a 404 error."""
    florist = (
        db.query(Florist)
        .filter(Florist.id == florist_id)
        .first()
    )

    if florist is None:
        raise HTTPException(
            status_code=404,
            detail="Florist not found.",
        )

    return florist
