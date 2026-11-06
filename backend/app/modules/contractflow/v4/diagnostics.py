"""Fixed validation metadata, never provider text, quotes or arbitrary IDs."""

from pydantic import ValidationError

FIELDS = frozenset("changes change_index additional_scope deliverable_proposal timeline compensation citations reference excerpt text response proposals request_snapshot original_agreement original_facts original_agreement_id original_agreement_version project_id assessment_id assessment_version verified_review rendered_text draft_id status notice effective human_review_required semantic_review_required parties_approved unresolved_terms version deterministic_validation".split())
CHECKS = frozenset("UNKNOWN_REFERENCE EXCERPT_NOT_EXACT DUPLICATE_REFERENCE REQUIRED_REQUEST_CITATION_MISSING REQUEST_EXCERPT_INCOMPLETE REVIEWED_ASSESSMENT_CITATION_MISSING ASSESSMENT_EXCERPT_INCOMPLETE AGREEMENT_CONTEXT_MISSING AUTHORITATIVE_FACT_CITATION_MISSING AUTHORITATIVE_FACT_EXCERPT_INCOMPLETE BASELINE_REFERENCE_NOT_GROUNDED BASELINE_ROLE_AMBIGUOUS MATERIAL_CONTENT_CONTRADICTION SCHEMA_MISSING SCHEMA_EXTRA_FIELD SCHEMA_INVALID INVALID_JSON RESPONSE_TYPE RESPONSE_SIZE PROPOSAL_LANGUAGE CONTENT_VOCABULARY CHANGE_COVERAGE MATERIAL_CONTENT PROVIDER_INCOMPLETE_OUTPUT".split())
CHECKS = CHECKS | {"WORDING_QUALITY"}
CATEGORIES = frozenset({"AGREEMENT", "REQUEST", "ASSESSMENT", "LEGACY_V3_REFERENCE", "UNKNOWN", "NONE"})


def safe_field(path):
    # Internal validator paths use integer indexes. Sanitized serialized paths
    # also allow numeric components only following known collection fields.
    result = []
    for part in path:
        if type(part) is int and 0 <= part < 1000:
            result.append(str(part))
        elif isinstance(part, str) and part in FIELDS:
            result.append(part)
        elif isinstance(part, str) and part.isascii() and part.isdigit() and len(part) <= 3 and result and result[-1] in {"changes", "citations"}:
            result.append(str(int(part)))
        else:
            result.append("<unrecognized_field>")
    return ".".join(result) or "response"


def category(reference):
    for prefix, name in (("agreement.", "AGREEMENT"), ("request.", "REQUEST"),
                         ("assessment.", "ASSESSMENT"), ("original.", "LEGACY_V3_REFERENCE")):
        if isinstance(reference, str) and reference.startswith(prefix):
            return name
    return "UNKNOWN"


def safe_token_metadata(metadata):
    result = {}
    for key in ("unsupported_unique_count", "unsupported_occurrence_count", "agreement_only_occurrence_count", "source_variant_occurrence_count"):
        value = metadata.get(key)
        if type(value) is int and 0 <= value <= 1600:
            result[key] = value
    positions = []
    candidates = metadata.get("unsupported_positions", [])
    if not isinstance(candidates, (list, tuple)):
        candidates = []
    for item in candidates[:20]:
        if not isinstance(item, dict):
            continue
        values = [item.get(key) for key in ("token_index", "start", "end")]
        if not all(type(v) is int and 0 <= v <= 1600 for v in values):
            continue
        if values[1] >= values[2] or item.get("character_class") not in {"ASCII", "NON_ASCII"}:
            continue
        positions.append(dict(zip(("token_index", "start", "end"), values)) | {"character_class": item["character_class"]})
    result["unsupported_positions"] = positions
    return result


def diagnostic(path=(), check="SCHEMA_INVALID", source_category="NONE", token_metadata=None):
    result = {"field": safe_field(path), "check": check if check in CHECKS else "SCHEMA_INVALID",
              "source_category": source_category if source_category in CATEGORIES else "UNKNOWN"}
    if check == "CONTENT_VOCABULARY" and isinstance(token_metadata, dict):
        result["token_metadata"] = safe_token_metadata(token_metadata)
    return result


def schema_diagnostics(error: ValidationError):
    issues = []
    for item in error.errors(include_input=False, include_context=False, include_url=False)[:20]:
        check = {"missing": "SCHEMA_MISSING", "extra_forbidden": "SCHEMA_EXTRA_FIELD",
                 "json_invalid": "INVALID_JSON"}.get(item["type"], "SCHEMA_INVALID")
        issues.append(diagnostic(item["loc"], check))
    return tuple(issues)
