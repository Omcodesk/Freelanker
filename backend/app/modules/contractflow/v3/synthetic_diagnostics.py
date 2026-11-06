"""Opt-in local explanation preview for exact, hash-pinned synthetic inputs only."""

import hashlib
import json
import re
import unicodedata

PINS = {
    "in_scope": ("IN_SCOPE", "35a31ba1b3b36391215062227a5c8a67a0246761833887ebb561fa6571cf1f75"),
    "out_of_scope": ("OUT_OF_SCOPE", "0a05cbfe8627a4f20bb917da94702122ad96c05dd77955c39253c5c6c7b37746"),
    "needs_clarification": ("NEEDS_CLARIFICATION", "b41ac690f699e315ae2205c40b6ed9d1ceb41efeda40934edff5998665a4979c"),
}


def require_synthetic_cases(cases, *, selected_scenario=None):
    if selected_scenario is not None and selected_scenario not in PINS:
        raise ValueError("Unknown synthetic diagnostic scenario")
    expected_names = (selected_scenario,) if selected_scenario is not None else tuple(PINS)
    if tuple(name for name, _, _ in cases) != expected_names:
        raise ValueError("Synthetic diagnostic inputs do not match pinned scenarios")
    for name, expected, data in cases:
        canonical = json.dumps(data.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if (expected, hashlib.sha256(canonical.encode()).hexdigest()) != PINS[name]:
            raise ValueError("Synthetic diagnostic inputs changed; preview disabled")


def sanitize_explanation(text, secret):
    if not isinstance(text, str) or len(text) > 2000:
        return "[Explanation unavailable or exceeds preview limit]"
    # Omit the WHOLE preview if it resembles credentials, headers or contact data.
    # Never return the matching token. Numeric project statements remain visible.
    sensitive = re.search(
        r"authorization|bearer|api[_ -]?key|password|secret|headers?|cookie|gsk_|sk-|"
        r"https?://|[\w.+-]+@[\w.-]+|\b\d{3}[- ]\d{2}[- ]\d{4}\b|\b\d{10,}\b",
        text, re.I,
    )
    if (secret and secret in text) or sensitive or any(unicodedata.category(c) == "Cf" for c in text):
        return "[Explanation omitted: potentially sensitive content]"
    return "".join(c if ord(c) >= 32 and ord(c) != 127 else " " for c in text)


class SyntheticExplanationProbe:
    """Used only by the explicit synthetic runner after the input-pin check."""

    def __init__(self, provider, secret):
        self.provider, self.secret = provider, secret
        self.preview = None
        self.field_previews = {}

    def preview_for(self, field):
        # Never traverse a diagnostic path or echo arbitrary provider field names.
        return self.field_previews.get(field)

    async def generate(self, **kwargs):
        self.preview = None
        self.field_previews = {}
        raw = await self.provider.generate(**kwargs)
        if isinstance(raw, str) and len(raw.encode("utf-8")) <= 64000:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and isinstance(parsed.get("explanation"), str):
                    self.preview = sanitize_explanation(parsed["explanation"], self.secret)
                    self.field_previews["analysis.explanation"] = self.preview
                impacts = parsed.get("potential_impacts") if isinstance(parsed, dict) else None
                if isinstance(impacts, list):
                    # Schema permits at most three impacts. Only their known
                    # explanation fields are eligible, not raw items or responses.
                    for index, impact in enumerate(impacts[:3]):
                        if isinstance(impact, dict) and isinstance(impact.get("explanation"), str):
                            self.field_previews[f"analysis.potential_impacts.{index}.explanation"] = sanitize_explanation(
                                impact["explanation"], self.secret
                            )
            except (ValueError, TypeError):
                pass
        return raw  # Never repair or bypass the actual service validation.
