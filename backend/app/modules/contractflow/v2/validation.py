"""Conservative lexical safeguards, not a semantic equivalence proof."""

import re
from collections import Counter

from ..schemas import ProjectInput, wording_sources

PROHIBITED = re.compile(
    r"\b(payment|payments|payable|deposit|instalments?|installments?|penalt\w*|"
    r"governing|jurisdiction|copyright|intellectual|ownership|licen[cs]\w*|"
    r"terminat\w*|cancel\w*|acceptance|accepted|deemed|warrant\w*|guarantee\w*|"
    r"indemn\w*|liabil\w*|refund\w*|interest|tax\w*|revisions?|unlimited|"
    r"confidential\w*|exclusive\w*|must|shall)\b", re.IGNORECASE,
)
NUMBER_WORDS = dict(zip(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split(),
    map(str, range(21)),
))


def quantities(text: str) -> Counter:
    tokens = re.findall(r"\d+(?:[.,]\d+)*|\b[a-z]+\b", text.casefold())
    return Counter(NUMBER_WORDS.get(t, t) for t in tokens if t in NUMBER_WORDS or t[0].isdigit())


def validate_wording(project: ProjectInput, sections) -> None:
    sources = wording_sources(project)
    if len(sections) != len(sources) or {s.source_ref for s in sections} != set(sources):
        raise ValueError("Every source must occur exactly once")
    for section in sections:
        original, proposed = sources[section.source_ref], section.text
        if PROHIBITED.search(proposed):
            raise ValueError("Potential legal/commercial term or unsupported obligation")
        # Facts such as dates and money belong only in deterministic sections.
        if re.search(r"[$€£₹%]|\b(?:USD|INR|EUR|GBP)\b", proposed):
            raise ValueError("Commercial values must not appear in AI wording")
        if quantities(proposed) != quantities(original):
            raise ValueError("Numeric content changed within a source paraphrase")
        if any(ord(c) < 32 for c in proposed):
            raise ValueError("AI wording must be a single plain-text paragraph")
        if re.search(r"\b(?:not|never|except|unless|excluding|without)\b", proposed, re.I) and not re.search(
            r"\b(?:not|never|except|unless|excluding|without)\b", original, re.I
        ):
            raise ValueError("New qualification or negation requires review before generation")
