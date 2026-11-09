from ..errors import ContractGenerationError, InvalidProviderOutput


class ReviewVerificationError(ContractGenerationError):
    """Review could not be authenticated or was stale/inconsistent."""


class AmendmentValidationError(InvalidProviderOutput):
    def __init__(self, rule="INVALID_AMENDMENT_OUTPUT", *, field=(), check="SCHEMA_INVALID", source_category="NONE", diagnostics=None, token_metadata=None):
        from .diagnostics import diagnostic

        allowed = {"INVALID_AMENDMENT_OUTPUT", "INVALID_EVIDENCE", "UNSUPPORTED_WORDING",
                   "UNSUPPORTED_CHANGE", "UNSAFE_PROPOSAL", "INCOMPLETE_COVERAGE"}
        self.rule = rule if rule in allowed else "INVALID_AMENDMENT_OUTPUT"
        self.diagnostics = tuple(diagnostic(d["field"].split("."), d["check"], d["source_category"], d.get("token_metadata"))
                                 for d in diagnostics[:20]) if diagnostics is not None else (
                                     diagnostic(field, check, source_category, token_metadata),)
        super().__init__(self.rule)
