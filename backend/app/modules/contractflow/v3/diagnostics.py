"""Allowlisted validation metadata only: never echo model values or messages."""

from pydantic import ValidationError

from ..errors import InvalidProviderOutput

FIELDS = frozenset("analysis classification explanation source_references reference excerpt requested_changes description request_evidence potential_impacts category clarification_questions context_references input_snapshot original_project request_id project_id recommended_action human_review_required semantic_review_required deterministic_validation version response client_request supporting_context title scope budget currency start_date deadline client freelancer id name deliverables milestones deliverable_ids text".split())
CODES = frozenset("SCHEMA_INVALID SCHEMA_MISSING SCHEMA_EXTRA_FIELD INVALID_JSON RESPONSE_TYPE RESPONSE_SIZE PROVIDER_INCOMPLETE_OUTPUT UNKNOWN_SOURCE_REFERENCE FABRICATED_EXCERPT DUPLICATE_REFERENCE MISSING_SCOPE_EVIDENCE MISSING_TIMELINE_EVIDENCE UNSUPPORTED_SCHEDULE_CHANGE QUANTIFIED_PROSE POTENTIAL_BINDING_TERM CONTROL_CHARACTER DUPLICATE_CHANGE DUPLICATE_IMPACT_CATEGORY CLARIFICATION_QUESTIONS_REQUIRED SNAPSHOT_MISMATCH ACTION_MISMATCH".split())
COLLECTIONS = frozenset("source_references requested_changes potential_impacts clarification_questions context_references request_evidence supporting_context deliverables milestones deliverable_ids".split())


def safe_field(location) -> str:
    parts = []
    for part in location:
        if isinstance(part, int) and 0 <= part < 10000:
            parts.append(str(part))
        elif isinstance(part, str) and part in FIELDS:
            parts.append(part)
        elif (isinstance(part, str) and part.isascii() and part.isdecimal() and len(part) <= 4
              and parts and parts[-1] in COLLECTIONS):
            parts.append(str(int(part)))
        else:
            parts.append("<unrecognized_field>")
    return ".".join(parts) or "analysis"


def issue(code, field, reference=None):
    result = {"rule": code if code in CODES else "SCHEMA_INVALID",
              "field": safe_field(field)}
    # References are passed only after lookup in the original allowlisted registry.
    # Additionally constrain their shape; external IDs and arbitrary paths never appear.
    import re
    if reference and re.fullmatch(
        r"original\.(?:scope|title|start_date|deadline|budget|currency|(?:deliverables|milestones)/\d+/(?:id|description|deadline|deliverable_ids/\d+))|request\.client_request|context/\d+",
        reference,
    ):
        result["reference"] = reference
    return result


class RuleViolation(ValueError):
    def __init__(self, code, field, reference=None):
        self.issue = issue(code, field, reference)
        super().__init__(self.issue["rule"])


class V3InvalidProviderOutput(InvalidProviderOutput):
    def __init__(self, issues):
        # Rebuild metadata so accidental unknown fields/codes cannot be printed.
        self.diagnostics = tuple(issue(i["rule"], i["field"].split("."), i.get("reference")) for i in issues)
        super().__init__("V3 response failed deterministic validation")


def validation_issues(error: ValidationError):
    result = []
    for item in error.errors(include_input=False, include_url=False):
        inner = item.get("ctx", {}).get("error")
        if isinstance(inner, RuleViolation):
            result.append(inner.issue)
        else:
            code = {"missing": "SCHEMA_MISSING", "extra_forbidden": "SCHEMA_EXTRA_FIELD",
                    "json_invalid": "INVALID_JSON"}.get(item["type"], "SCHEMA_INVALID")
            result.append(issue(code, item["loc"]))
    return result[:20]
