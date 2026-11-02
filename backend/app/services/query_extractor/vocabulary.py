"""Explicit bilingual aliases; no fuzzy matching or general plural stemming."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping  # noqa: UP035 -- keep the evaluated v1 core unchanged

from .contracts import FlowerVocabulary
from .text import Token, tokens

ALIASES: Mapping[str, tuple[str, ...]] = {
    "Rose": ("rose", "roses", "rosa", "rosas"),
    "Lily": ("lily", "lilies", "lírio", "lírios"),
    "Tulip": ("tulip", "tulips", "tulipa", "tulipas"),
    "Daisy": ("daisy", "daisies", "margarida", "margaridas"),
    "Carnation": ("carnation", "carnations", "cravo", "cravos"),
    "Gerbera": ("gerbera", "gerberas", "gérbera", "gérberas"),
    "Hydrangea": ("hydrangea", "hydrangeas", "hortênsia", "hortênsias"),
    "Peony": ("peony", "peonies", "peônia", "peônias"),
    "Sunflower": ("sunflower", "sunflowers", "girassol", "girassóis"),
    "Baby's Breath": ("baby's breath", "baby’s breath", "mosquitinho", "mosquitinhos"),
}


@dataclass(frozen=True)
class FlowerMention:
    """Longest matching alias; multiple canonical targets are never chosen silently."""

    first: int
    after: int
    names: tuple[str, ...]


class CatalogMatcher:
    """Index only canonical names and aliases available in this catalog snapshot."""

    def __init__(
        self, catalog: FlowerVocabulary,
        aliases: Mapping[str, tuple[str, ...]] = ALIASES,
    ) -> None:
        index: dict[tuple[str, ...], list[str]] = defaultdict(list)
        for name in catalog.flowers:
            for alias in (name, *aliases.get(name, ())):
                key = tuple(token.word for token in tokens(alias))
                if key and name not in index[key]:
                    index[key].append(name)
        self._index = {key: tuple(names) for key, names in index.items()}
        self._lengths = sorted({len(key) for key in index}, reverse=True)

    def find(self, words: tuple[Token, ...]) -> tuple[FlowerMention, ...]:
        """Prefer longest token matches, preserving ambiguous aliases as candidates."""
        found = []
        position = 0
        while position < len(words):
            for length in self._lengths:
                key = tuple(token.word for token in words[position:position + length])
                if len(key) == length and key in self._index:
                    found.append(FlowerMention(position, position + length, self._index[key]))
                    position += length
                    break
            else:
                position += 1
        return tuple(found)
