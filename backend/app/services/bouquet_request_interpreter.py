"""Interface for interpreting bouquet requests written in natural language."""

from typing import Protocol

from app.schemas.bouquet_interpretation import BouquetInterpretation


class BouquetRequestInterpreter(Protocol):
    """Extract structured bouquet requirements from customer text."""

    def interpret(self, text: str) -> BouquetInterpretation:
        """Return requirements identified in the supplied text."""
        ...
