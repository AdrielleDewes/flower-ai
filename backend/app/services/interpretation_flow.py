"""Stateless POC orchestration; interpretation never generates or saves a bouquet."""

import logging
from time import perf_counter

from sqlalchemy.orm import Session

from app.schemas.interpretation import InterpretationRequest, InterpretationResponse
from app.services.catalog import get_interpretation_catalog
from app.services.interpretation_merger import merge_interpretations
from app.services.llm_bouquet_request_interpreter import LLMBouquetRequestInterpreter
from app.services.llm_provider import InvalidLLMOutputError, LLMProvider
from app.services.query_extractor import FlowerVocabulary, QueryExtractor

logger = logging.getLogger(__name__)


def interpret_bouquet_request(
    db: Session, florist_id: int, request: InterpretationRequest, provider: LLMProvider,
) -> InterpretationResponse:
    """Interpret once with complementary sources and return a reviewable proposal."""
    started = perf_counter()
    catalog = get_interpretation_catalog(db, florist_id).model_copy(deep=True)
    extraction = QueryExtractor(FlowerVocabulary(tuple(catalog.flowers))).extract(request.text)
    llm = LLMBouquetRequestInterpreter(provider, catalog, catalog_constraints=True).interpret(request.text)
    try:
        merged = merge_interpretations(llm, extraction, catalog)
    except ValueError as exc:
        raise InvalidLLMOutputError("The interpretation contains invalid preference values.") from exc
    logger.info(
        "Bouquet interpretation completed",
        extra={
            "florist_id": florist_id, "requires_review": merged.requires_review,
            "issue_count": len(merged.issues), "duration_seconds": perf_counter() - started,
        },
    )
    return InterpretationResponse(**merged.model_dump(), text=request.text, options=catalog)
