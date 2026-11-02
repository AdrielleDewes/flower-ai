"""Unicode matching with offsets into the unmodified original query."""

import re
import unicodedata
from dataclasses import dataclass

from .contracts import Evidence


def normalize(text: str) -> str:
    """Fold spelling for matching only; never use these indices as evidence offsets."""
    return "".join(
        char for char in unicodedata.normalize("NFD", text.casefold())
        if not unicodedata.combining(char)
    )


@dataclass(frozen=True)
class Token:
    """Normalized token with original character boundaries."""

    word: str
    start: int
    end: int


def tokens(text: str, offset: int = 0) -> tuple[Token, ...]:
    """Tokenize accents and apostrophes without substring flower matches."""
    return tuple(
        Token(normalize(match.group()), offset + match.start(), offset + match.end())
        for match in re.finditer(r"(?:[^\W_]|[\u0300-\u036f])+", text)
    )


@dataclass(frozen=True)
class Clause:
    """A bounded context for a deliberately small set of extraction constructions."""

    start: int
    end: int
    text: str

    @property
    def words(self) -> str:
        """Return token-normalized context for rule matching."""
        return " ".join(token.word for token in tokens(self.text))

    def evidence(self, rule_id: str) -> Evidence:
        """Keep the cue and its argument together, not just an isolated keyword."""
        return Evidence(self.start, self.end, self.text, rule_id)


def clauses(query: str) -> tuple[Clause, ...]:
    """Split sentence/contrast boundaries, preserving decimals and coordinated lists."""
    separator = r"[;!?\n]+|(?<!\.)\.(?![\d.])|\b(?:mas|but|porém|porem)\b"
    result = []
    start = 0
    for match in (*re.finditer(separator, query, re.IGNORECASE), None):
        end = match.start() if match is not None else len(query)
        left = start
        while left < end and query[left].isspace():
            left += 1
        while end > left and query[end - 1].isspace():
            end -= 1
        if end > left:
            result.append(Clause(left, end, query[left:end]))
        if match is not None:
            start = match.end()
    return tuple(result)
