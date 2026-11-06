"""Explicit source-conditioned word forms, not embeddings or open synonym expansion."""

from dataclasses import dataclass
import re
import unicodedata

PARAPHRASES = {
    "integration": frozenset({"integration", "integrate", "integrates", "integrated", "integrating"}),
    "payment": frozenset({"payment", "payments"}),
}
TOKEN = re.compile(r"[^\W\d_]+(?:[\u0300-\u036f]+[^\W\d_]*)*", re.UNICODE)


@dataclass(frozen=True)
class Token:
    value: str
    start: int
    end: int
    index: int


def tokens(text):
    return tuple(Token(unicodedata.normalize("NFC", m.group().casefold()), m.start(), m.end(), i)
                 for i, m in enumerate(TOKEN.finditer(text)))


def normalized_words(text):
    return {t.value for t in tokens(text)}


def active_forms(content):
    source = normalized_words(content)
    return {canonical: forms for canonical, forms in PARAPHRASES.items() if source & forms}


def canonical(word, forms):
    return next((key for key, variants in forms.items() if word in variants), word)


def content_terms(text, content):
    forms = active_forms(content)
    return {canonical(word, forms) for word in normalized_words(text)}


def assess_vocabulary(text, content, connectives, agreement_content="", *, ignored_spans=()):
    forms = active_forms(content)
    source = {canonical(word, forms) for word in normalized_words(content)}
    allowed = source | connectives
    parsed = tokens(text)
    parsed = tuple(t for t in parsed if not any(start <= t.start and t.end <= end for start, end in ignored_spans))
    unsupported = [t for t in parsed if canonical(t.value, forms) not in allowed]
    agreement = normalized_words(agreement_content)
    metadata = {
        "unsupported_unique_count": len({t.value for t in unsupported}),
        "unsupported_occurrence_count": len(unsupported),
        "agreement_only_occurrence_count": sum(t.value in agreement for t in unsupported),
        "source_variant_occurrence_count": sum(t.value != canonical(t.value, forms) for t in parsed),
        "unsupported_positions": [
            {"token_index": t.index, "start": t.start, "end": t.end,
             "character_class": "ASCII" if t.value.isascii() else "NON_ASCII"}
            for t in unsupported[:20]
        ],
    }
    return not unsupported, metadata


def wording_rules(content, material_description, connectives):
    forms = active_forms(content)
    return {
        "preferred_source_terms": sorted(normalized_words(content)),
        "permitted_source_conditioned_forms": {key: sorted(values) for key, values in forms.items()},
        "required_material_terms": sorted(content_terms(material_description, content) - connectives),
    }
