"""Conservative, evidence-bearing bouquet query rules; no inference or I/O."""

import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from .contracts import (
    FIELDS,
    Candidate,
    ExtractedValue,
    ExtractionState,
    FieldExtraction,
    FlowerVocabulary,
    QueryExtraction,
)
from .text import Clause, clauses, normalize, tokens
from .vocabulary import CatalogMatcher

_SIZE = {
    "small": "SMALL", "pequeno": "SMALL", "pequena": "SMALL",
    "pequenos": "SMALL", "pequenas": "SMALL",
    "medium": "MEDIUM", "medio": "MEDIUM", "media": "MEDIUM",
    "medios": "MEDIUM", "medias": "MEDIUM",
    "large": "LARGE", "grande": "LARGE", "grandes": "LARGE",
}
_BOUQUET = re.compile(r"\b(?:bouquet|bouquets|buque|buques)\b")
_REQUEST = re.compile(r"\b(?:quero|prefiro|inclua|coloque|want|prefer|include|use|make)\b")
_IRRELEVANT = re.compile(
    r"\b(?:portaria|entrada|apartamento|apartment|endereco|address|parede|wall|"
    r"vaso|vase|embalagem|wrapping|fita|ribbon|delivery|entrega|entregador|"
    r"retirar|buscar|destinatario|recipient|vestido|dress)\b"
)
_NARRATIVE = re.compile(
    r"\b(?:disse|said|says|gosta|likes|liked|comprou|bought|has|had|tinha|tem)\b"
)
_UNCERTAIN = re.compile(
    r"\b(?:talvez|maybe|perhaps|nao sei|not sure|nao decidi|not decided|"
    r"ainda nao escolhi|have not decided|nao tenho certeza|could|might|poderia|if|se)\b"
)
_NO_PREFERENCE = re.compile(
    r"\b(?:no preference|sem preferencia|nao tenho preferencia|no particular|"
    r"nao escolhi|have not chosen)\b"
)
_COMPLEX_NEGATION = re.compile(
    r"\b(?:not without|nao .* sem|(?:do not|don t) (?:want to )?avoid|"
    r"nao evite|nao quero evitar|without no)\b"
)
_FLOWER_CUE = re.compile(
    r"\b(?:(?P<negative>nao (?:use|coloque|inclua|quero)|"
    r"(?:do not|don t) (?:use|include|want)|cannot use|can t use|nao posso usar|nada de|leave out|"
    r"sem|without|avoid|excluding|no|not|nao)|"
    r"(?P<positive>com|with|quero|prefiro|inclua|coloque|want|prefer|include|use))\b"
)
_LINK_WORDS = {
    "and", "e", "nem", "or", "ou", "please", "por", "favor",
    "red", "white", "blue", "pink", "yellow", "purple", "orange",
    "vermelhas", "vermelhos", "brancas", "brancos", "amarelas", "amarelos",
}
_MONEY = r"(?:r\$\s*|brl\s*)?(\d+(?:[.,]\d+)*)(?![\w.,])(?:\s*(?:reais|brl))?"
_UPPER_BOUND = re.compile(
    r"\b(?:ate|no maximo|maximum|maximo|under|up to|at most|no more than)\s*" + _MONEY
)
_BUDGET_VALUE = re.compile(
    r"\b(?:budget|orcamento)\s*(?:is|of|e|de|:)?\s*" + _MONEY
)
_RANGE = re.compile(
    r"\b(?:between|entre|de)\s*" + _MONEY + r"\s*(?:and|e|a|to)\s*" + _MONEY
)
_FOREIGN_CURRENCY = re.compile(
    r"(?<!r)\$|\b(?:usd|eur|gbp)(?=\d|\s|$)|\b(?:dollars|dolares|euros|pounds)\b"
)


def _amount(raw: str) -> Decimal | None:
    """Accept unambiguous numerals; a single three-digit suffix is ambiguous."""
    if raw.isdigit():
        value = raw
    elif re.fullmatch(r"\d+[.,]\d{1,2}", raw):
        value = raw.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d{1,2}", raw):
        value = raw.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:,\d{3})+\.\d{1,2}", raw):
        value = raw.replace(",", "")
    else:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() and parsed > 0 else None


def _finish(candidates: list[Candidate], scalar: bool = False) -> FieldExtraction:
    """Resolve duplicates, withholding all values when a field is uncertain."""
    groups: dict[str | Decimal, list] = defaultdict(list)
    for candidate in candidates:
        if candidate.value is not None and candidate.reason is None:
            groups[candidate.value].extend(candidate.evidence)
    reasons = tuple(dict.fromkeys(c.reason for c in candidates if c.reason))
    if scalar and len(groups) > 1:
        return FieldExtraction(
            ExtractionState.CONFLICT, candidates=tuple(candidates),
            reasons=(*reasons, "incompatible_values"),
        )
    if reasons:
        return FieldExtraction(
            ExtractionState.AMBIGUOUS, candidates=tuple(candidates), reasons=reasons,
        )
    values = tuple(
        ExtractedValue(value, tuple(dict.fromkeys(evidence)))
        for value, evidence in groups.items()
    )
    return FieldExtraction(
        ExtractionState.RESOLVED if values else ExtractionState.ABSENT,
        values=values, candidates=tuple(candidates),
    )


class QueryExtractor:
    """Extract four fields using a fixed catalog snapshot and bounded context rules."""

    def __init__(self, catalog: FlowerVocabulary) -> None:
        """Build a tenant-local vocabulary index without production dependencies."""
        self._matcher = CatalogMatcher(catalog)

    def extract(self, query: str) -> QueryExtraction:
        """Return values and evidence, abstaining on unsupported or unclear language."""
        if not isinstance(query, str):
            raise TypeError("Query must be a string.")
        candidates: dict[str, list[Candidate]] = {field: [] for field in FIELDS}
        for clause in clauses(query):
            words = clause.words
            # These conservative exclusions avoid mistaking descriptions for requests.
            if _IRRELEVANT.search(words) or _NARRATIVE.search(words):
                continue
            if any(mark in clause.text for mark in ('"', '“', '”', '«', '»')):
                continue
            self._size(clause, candidates["size"])
            self._budget(clause, candidates["budget_max"])
            self._flowers(clause, candidates)
        fields = {
            name: _finish(found, scalar=name in {"size", "budget_max"})
            for name, found in candidates.items()
        }
        positive = {c.value for c in candidates["preferred_flowers"] if c.reason is None}
        negative = {c.value for c in candidates["excluded_flowers"] if c.reason is None}
        if positive & negative:
            for name in ("preferred_flowers", "excluded_flowers"):
                fields[name] = FieldExtraction(
                    ExtractionState.CONFLICT, candidates=tuple(candidates[name]),
                    reasons=("flower_requested_and_excluded",),
                )
        return QueryExtraction(**fields)

    @staticmethod
    def _size(clause: Clause, found: list[Candidate]) -> None:
        words = clause.words
        if _NO_PREFERENCE.search(words):
            return
        mentions = [token for token in tokens(clause.text) if token.word in _SIZE]
        if not mentions:
            return
        bare = set(words.split()) <= {*_SIZE, "size", "tamanho", "please", "por", "favor", "or", "ou"}
        if not (
            _BOUQUET.search(words) or re.search(r"\b(?:size|tamanho)\b", words)
            or bare or _UNCERTAIN.search(words)
        ):
            return
        reason = None
        if _UNCERTAIN.search(words) or re.search(r"\b(?:ou|or)\b", words):
            reason = "undecided_size"
        elif re.search(r"\b(?:not|nao|sem|without)\b", words):
            reason = "negated_or_unclear_size"
        for token in mentions:
            found.append(Candidate(_SIZE[token.word], (clause.evidence("size.explicit"),), reason))

    @staticmethod
    def _budget(clause: Clause, found: list[Candidate]) -> None:
        text = normalize(clause.text)
        if not re.search(r"r\$|\b(?:brl|reais|budget|orcamento|gastar|spend|spending)\b", text):
            return
        if re.search(r"\b(?:not my budget|nao e meu orcamento|no budget|sem orcamento)\b", clause.words):
            return
        ranges = list(_RANGE.finditer(text)) if re.search(r"r\$|\b(?:budget|orcamento|reais|brl)\b", text) else []
        matches = [(match, match.group(2), "budget.range_upper") for match in ranges]
        for pattern in (_UPPER_BOUND, _BUDGET_VALUE):
            matches.extend(
                (match, match.group(1), "budget.explicit_upper")
                for match in pattern.finditer(text)
                if not any(r.start() <= match.start() < r.end() for r in ranges)
            )
        if not matches and _FOREIGN_CURRENCY.search(text) and re.search(r"\d", text):
            found.append(Candidate(
                None, (clause.evidence("budget.unsupported_currency"),), "unsupported_currency",
            ))
        for match, raw, rule in matches:
            value = _amount(raw)
            reason = None
            if _FOREIGN_CURRENCY.search(text):
                reason = "unsupported_currency"
            elif _UNCERTAIN.search(clause.words) or re.search(r"\b(?:not|nao|or|ou)\b", clause.words):
                reason = "uncertain_budget"
            elif value is None:
                reason = "ambiguous_or_invalid_amount"
            elif rule == "budget.range_upper":
                lower = _amount(match.group(1))
                if lower is None or lower > value:
                    reason = "ambiguous_or_reversed_range"
            found.append(Candidate(value, (clause.evidence(rule),), reason))

    def _flowers(self, clause: Clause, found: dict[str, list[Candidate]]) -> None:
        words = tokens(clause.text)
        mentions = self._matcher.find(words)
        if not mentions or _NO_PREFERENCE.search(clause.words):
            return
        flower_positions = {index for m in mentions for index in range(m.first, m.after)}
        floral_words = {words[index].word for index in flower_positions}
        bare = all(index in flower_positions or token.word in _LINK_WORDS for index, token in enumerate(words))
        for mention in mentions:
            prefix = " ".join(t.word for t in words[:mention.first])
            cues = list(_FLOWER_CUE.finditer(prefix))
            negative = bool(cues and cues[-1].group("negative"))
            reason = None
            if negative:
                gap = prefix[cues[-1].end():].split()
                if any(word not in _LINK_WORDS | floral_words and not word.isdigit() for word in gap):
                    reason = "unclear_negation_scope"
            else:
                cue = cues[-1] if cues else None
                # 'with' inside a narrative is not enough to establish a preference.
                contextual = _REQUEST.search(clause.words) or _BOUQUET.search(clause.words)
                coordinated = bool(cues and cues[0].start() == 0) and all(
                    word in _LINK_WORDS | floral_words or word.isdigit()
                    for word in _FLOWER_CUE.sub("", prefix).split()
                )
                if not (bare or (cue and (contextual or cue.start() == 0 or coordinated))):
                    continue
            if _UNCERTAIN.search(clause.words) or re.search(r"\b(?:ou|or)\b", clause.words):
                reason = "undecided_flower"
            if _COMPLEX_NEGATION.search(clause.words):
                reason = "unsupported_negation"
            if len(mention.names) > 1:
                reason = "ambiguous_catalog_alias"
            # Singular rosa can describe a hue; require a floral relation or plural.
            surface = [t.word for t in words[mention.first:mention.after]]
            if surface == ["rosa"]:
                before = words[mention.first - 1].word if mention.first else ""
                if before not in {"com", "sem", "uma", "1"}:
                    reason = "ambiguous_rosa_color_or_flower"
            field = "excluded_flowers" if negative else "preferred_flowers"
            rule = "flower.explicit_exclusion" if negative else "flower.explicit_preference"
            for name in mention.names:
                found[field].append(Candidate(name, (clause.evidence(rule),), reason))
