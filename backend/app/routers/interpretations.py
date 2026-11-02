"""Interpretation drafts for user review, separate from recommendation requests."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_florist, get_interpretation_provider
from app.models.florist import Florist
from app.schemas.interpretation import InterpretationRequest, InterpretationResponse
from app.services.interpretation_flow import interpret_bouquet_request
from app.services.llm_provider import (
    InvalidLLMOutputError,
    LLMProvider,
    LLMProviderError,
)

router = APIRouter(tags=["interpretations"])
logger = logging.getLogger(__name__)


@router.post(
    "/florists/{florist_id}/interpretations", response_model=InterpretationResponse,
    responses={
        404: {"description": "Florist not found"},
        502: {"description": "Invalid interpretation response"},
        503: {"description": "Interpretation service unavailable"},
    },
)
def create_interpretation(
    request: InterpretationRequest,
    florist: Florist = Depends(get_florist),  # noqa: B008
    provider: LLMProvider = Depends(get_interpretation_provider),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> InterpretationResponse:
    """Return a proposal without calling recommendation or persistence services."""
    try:
        return interpret_bouquet_request(db, florist.id, request, provider)
    except InvalidLLMOutputError as exc:
        logger.warning("Invalid interpretation response", extra={"florist_id": florist.id})
        raise HTTPException(status_code=502, detail="The interpretation response was invalid.") from exc
    except (LLMProviderError, SQLAlchemyError) as exc:
        logger.warning("Interpretation service unavailable", extra={"florist_id": florist.id})
        raise HTTPException(status_code=503, detail="Interpretation service is unavailable.") from exc
