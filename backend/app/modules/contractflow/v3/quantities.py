"""Conservative quantity claims: value + unit + subject + cited baseline role.

Only website page counts are currently understood. All other numeric claims
remain subject to the rejecting prose filter; this is not an entailment model.
"""

from dataclasses import dataclass
import re

WORDS = dict(zip("one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split(), range(1, 21)))
NUMBER = r"(?:[1-9]\d{0,2}|" + "|".join(WORDS) + r")"
FORWARD = re.compile(rf"\b(?P<count>{NUMBER})[- ]pages?\s+(?P<subject>(?:[A-Za-z]+\s+){{0,3}}(?:website|site))\b", re.I)
REVERSE = re.compile(rf"\b(?P<subject>(?:[A-Za-z]+\s+){{0,3}}(?:website|site))\s+(?:with|of|comprising|containing|consisting of|has|contains|includes)\s+(?P<count>{NUMBER})\s+pages\b", re.I)
IGNORED = frozenset("a an the responsive build building develop developing create creating original agreed existing project scope baseline".split())
# Explicit, one-code-point substitutions in a temporary matching view only.
# Do not use blanket Unicode normalization: source excerpts must remain exact,
# and range dashes, mathematical minus signs and invisible separators differ.
HYPHEN_TRANSLATION = str.maketrans({"\u2010": "-", "\u2011": "-", "\ufe63": "-", "\uff0d": "-"})


@dataclass(frozen=True)
class QuantityClaim:
    value: int
    unit: str
    subject: tuple[str, ...]
    start: int
    end: int

    @property
    def key(self):
        return self.value, self.unit, self.subject


def extract_quantities(text: str) -> tuple[QuantityClaim, ...]:
    matching_text = text.translate(HYPHEN_TRANSLATION)
    result = []
    seen = set()
    for pattern in (FORWARD, REVERSE):
        for match in pattern.finditer(matching_text):
            count = match.group("count").casefold()
            subject = tuple("website" if token == "site" else token for token in
                            re.findall(r"[a-z]+", match.group("subject").casefold()) if token not in IGNORED)
            # Translation preserves length, so spans address the untouched text.
            start, end = match.span("count")
            if (start, end) not in seen:
                result.append(QuantityClaim(WORDS[count] if count in WORDS else int(count), "pages", subject, start, end))
                seen.add((start, end))
    return tuple(result)


def _baseline_role(text: str, claim: QuantityClaim) -> bool:
    prefix = re.split(r"[.!?;\n]", text[:claim.start])[-1][-200:]
    anchors = list(re.finditer(r"\b(?:original|agreed|existing|baseline)\b", prefix, re.I))
    if not anchors:
        return False
    anchor = anchors[-1]
    tail = prefix[anchor.end():]
    if re.search(r"\b(?:add|adds|adding|new|extra|additional|increase\w*|expand\w*|estimate\w*|will|should|could|would|propos\w*)\b", tail, re.I):
        return False
    # An imperative applied to an agreed item is still proposed work, not a fact.
    if re.search(r"\b(?:add|build|create|deliver|provide|implement|produce|increase|expand|charge|pay)\s+(?:(?:to|for|into)\s+)?(?:(?:a|an|the|another|new|additional)\s+)?$",
                 prefix[:anchor.start()], re.I):
        return False
    return True


def grounded_count_spans(text: str, registry: dict[str, str], evidence) -> tuple[tuple[int, int], ...]:
    supported = set()
    for citation in evidence:
        ref = citation.reference
        if ref != "original.scope" and not re.fullmatch(r"original\.deliverables/\d+/description", ref):
            continue
        source = registry.get(ref)
        if source is None or citation.excerpt not in source:
            continue
        # The citation itself must contain the complete quantitative fact; a
        # partial excerpt or an unrelated number cannot justify the claim.
        source_keys = {claim.key for claim in extract_quantities(source)}
        supported.update(claim.key for claim in extract_quantities(citation.excerpt) if claim.key in source_keys)
    return tuple((claim.start, claim.end) for claim in extract_quantities(text)
                 if claim.key in supported and _baseline_role(text, claim))


def ungrounded_numeric_text(text: str, registry: dict[str, str], evidence) -> str:
    spans = grounded_count_spans(text, registry, evidence)
    # Only supported quantity tokens are masked. All surrounding financial/date
    # content and all obligation wording remain available to existing checks.
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + "grounded" + text[end:]
    return text
