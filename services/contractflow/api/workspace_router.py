"""
Project-scoped ContractFlow workspace and review-issuance endpoints.

Kept separate from api/router.py so the core V6 APIRouter preserves its exact
8-route contract while exposing project overview, V4 assessment review receipts,
and V5 amendment review grants for the integrated Workspace UI.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import Field

from ..adapters.db import get_connection
from ..integrations.contracts import IntegrationError
from ..schemas import Schema
from ..v4.review import fingerprint
from ..v4.schemas import ReviewedAssessment
from ..v5.schemas import ApprovalSubject, Digest, canonical_digest
from .dependencies import get_principal, get_runtime
from .errors import SafeRoute

workspace_router = APIRouter(
    prefix="/api/v1/contractflow/workspace",
    tags=["ContractFlow Workspace"],
    route_class=SafeRoute,
)


class AssessmentReviewBody(Schema):
    expected_version: Annotated[int, Field(strict=True, ge=1)]
    expected_digest: Digest
    confirm_human_review: Literal[True]


class AmendmentReviewBody(Schema):
    expected_version: Annotated[int, Field(strict=True, ge=1)]
    expected_digest: Digest
    human_review: Literal[True]
    semantic_review: Literal[True]
    expires_in_hours: Annotated[int, Field(strict=True, ge=1, le=168)] = 24


class RevokeReviewBody(Schema):
    reason: Annotated[str, Field(strict=True, min_length=1, max_length=500)]


def _parse_jsonb(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


@workspace_router.get("/projects/{project_id}/overview")
async def get_project_overview(
    project_id: UUID,
    principal=Depends(get_principal),
    runtime=Depends(get_runtime),
):
    """List authorized ContractFlow artifacts, review grants, and readiness status for a project."""
    await runtime.auth.authorize(principal, str(project_id), None, write=False)

    # Check source readiness without failing the whole overview if setup is incomplete
    source_ready = False
    missing_requirements: list[str] = []
    source_version = 1
    has_active_agreement = False

    async for conn in get_connection():
        proj_row = await conn.fetchrow(
            """
            SELECT id, client_id, freelancer_id, total_budget, COALESCE(source_version, 1) AS source_version
            FROM public.projects
            WHERE id = $1
            """,
            project_id,
        )
        if not proj_row:
            raise IntegrationError("NOT_FOUND")
        source_version = int(proj_row["source_version"])
        if not proj_row["client_id"] or not proj_row["freelancer_id"]:
            missing_requirements.append("Both client and freelancer must join the project.")
        if proj_row["total_budget"] is None or proj_row["total_budget"] <= 0:
            missing_requirements.append("A positive project budget is required.")

        milestone_rows = await conn.fetch(
            "SELECT id, due_date FROM public.milestones WHERE project_id = $1",
            project_id,
        )
        if not milestone_rows:
            missing_requirements.append("At least one planned milestone with a due date is required.")
        elif any(m["due_date"] is None for m in milestone_rows):
            missing_requirements.append("Every milestone must have an explicit due date.")

        ag_row = await conn.fetchrow(
            """
            SELECT id, version_number, status
            FROM public.agreements
            WHERE project_id = $1 AND is_current = TRUE AND status IN ('approved', 'active')
            LIMIT 1
            """,
            project_id,
        )
        has_active_agreement = ag_row is not None
        source_ready = len(missing_requirements) == 0

        artifact_rows = await conn.fetch(
            """
            SELECT artifact_id, revision, kind, source_version, payload_json, content_digest, created_at
            FROM public.cf_artifacts
            WHERE project_id = $1
            ORDER BY created_at DESC, revision DESC
            """,
            project_id,
        )

        assessment_rev_rows = await conn.fetch(
            """
            SELECT ar.assessment_review_id, ar.review_reference, ar.assessment_id, ar.assessment_revision,
                   ar.original_agreement_id, ar.original_agreement_version, ar.reviewer_id,
                   ar.decision, ar.reviewed_at, ar.revoked
            FROM public.cf_assessment_reviews ar
            JOIN public.cf_artifacts art
              ON art.artifact_id = ar.assessment_id AND art.revision = ar.assessment_revision
            WHERE art.project_id = $1
            ORDER BY ar.created_at DESC
            """,
            project_id,
        )

        version_rows = await conn.fetch(
            """
            SELECT v.amendment_id, v.revision, v.state, v.content_digest AS approval_digest,
                   v.original_agreement_id, v.original_agreement_version, v.review_reference,
                   v.created_at, (h.current_revision = v.revision) AS is_current_head
            FROM public.cf_approval_versions v
            LEFT JOIN public.cf_approval_heads h
              ON h.amendment_id = v.amendment_id
            JOIN public.cf_artifacts art
              ON art.artifact_id = v.amendment_id AND art.revision = v.revision
            WHERE art.project_id = $1
            """,
            project_id,
        )

        review_rows = await conn.fetch(
            """
            SELECT r.review_id, r.amendment_id, r.revision, r.content_digest, r.reviewer_id,
                   r.reviewed_at, r.expires_at, r.human_review, r.semantic_review, r.revoked,
                   r.revoked_at, r.revocation_reason
            FROM public.cf_reviews r
            JOIN public.cf_artifacts art
              ON art.artifact_id = r.amendment_id AND art.revision = r.revision
            WHERE art.project_id = $1
            ORDER BY r.created_at DESC
            """,
            project_id,
        )

        decision_rows = await conn.fetch(
            """
            SELECT d.decision_id, d.amendment_id, d.revision, d.actor_id, d.role,
                   d.decision, d.rejection_reason, d.idempotency_key, d.created_at
            FROM public.cf_decisions d
            JOIN public.cf_artifacts art
              ON art.artifact_id = d.amendment_id AND art.revision = d.revision
            WHERE art.project_id = $1
            ORDER BY d.created_at ASC
            """,
            project_id,
        )

    versions_by_key = {(str(r["amendment_id"]), int(r["revision"])): r for r in version_rows}
    reviews_by_key: dict[tuple[str, int], list[dict]] = {}
    for r in review_rows:
        key = (str(r["amendment_id"]), int(r["revision"]))
        reviews_by_key.setdefault(key, []).append(
            {
                "review_id": str(r["review_id"]),
                "amendment_id": str(r["amendment_id"]),
                "revision": int(r["revision"]),
                "content_digest": r["content_digest"],
                "reviewer_id": str(r["reviewer_id"]),
                "reviewed_at": _iso(r["reviewed_at"]),
                "expires_at": _iso(r["expires_at"]),
                "human_review": bool(r["human_review"]),
                "semantic_review": bool(r["semantic_review"]),
                "revoked": bool(r["revoked"]),
                "revoked_at": _iso(r["revoked_at"]),
                "revocation_reason": r["revocation_reason"],
            }
        )

    decisions_by_key: dict[tuple[str, int], list[dict]] = {}
    for d in decision_rows:
        key = (str(d["amendment_id"]), int(d["revision"]))
        decisions_by_key.setdefault(key, []).append(
            {
                "decision_id": str(d["decision_id"]),
                "actor_id": str(d["actor_id"]),
                "role": d["role"],
                "decision": d["decision"],
                "rejection_reason": d["rejection_reason"],
                "created_at": _iso(d["created_at"]),
            }
        )

    assessment_reviews_by_key: dict[tuple[str, int], list[dict]] = {}
    for ar in assessment_rev_rows:
        key = (str(ar["assessment_id"]), int(ar["assessment_revision"]))
        assessment_reviews_by_key.setdefault(key, []).append(
            {
                "assessment_review_id": str(ar["assessment_review_id"]),
                "review_reference": ar["review_reference"],
                "assessment_id": str(ar["assessment_id"]),
                "assessment_revision": int(ar["assessment_revision"]),
                "original_agreement_id": str(ar["original_agreement_id"]),
                "original_agreement_version": int(ar["original_agreement_version"]),
                "reviewer_id": str(ar["reviewer_id"]),
                "decision": ar["decision"],
                "reviewed_at": _iso(ar["reviewed_at"]),
                "revoked": bool(ar["revoked"]),
            }
        )

    artifacts = []
    for row in artifact_rows:
        art_id = str(row["artifact_id"])
        rev = int(row["revision"])
        payload_dict = _parse_jsonb(row["payload_json"])
        item = {
            "artifact_id": art_id,
            "revision": rev,
            "kind": row["kind"],
            "source_version": int(row["source_version"]),
            "content_digest": row["content_digest"],
            "created_at": _iso(row["created_at"]),
            "payload": payload_dict,
        }
        if row["kind"] == "ASSESSMENT":
            item["assessment_reviews"] = assessment_reviews_by_key.get((art_id, rev), [])
        elif row["kind"] == "AMENDMENT":
            from ..v4.schemas import AmendmentDraft

            try:
                draft_obj = AmendmentDraft.model_validate(payload_dict)
                item["approval_digest"] = canonical_digest(rev, draft_obj)
            except Exception:
                item["approval_digest"] = None
            ver = versions_by_key.get((art_id, rev))
            item["approval_head"] = (
                {
                    "current_revision": int(ver["revision"]),
                    "is_current_head": bool(ver["is_current_head"]),
                    "state": ver["state"],
                    "approval_digest": ver["approval_digest"],
                    "original_agreement_id": str(ver["original_agreement_id"]),
                    "original_agreement_version": int(ver["original_agreement_version"]),
                    "review_reference": ver["review_reference"],
                    "created_at": _iso(ver["created_at"]),
                }
                if ver
                else None
            )
            item["reviews"] = reviews_by_key.get((art_id, rev), [])
            item["decisions"] = decisions_by_key.get((art_id, rev), [])
        artifacts.append(item)

    return {
        "project_id": str(project_id),
        "source_version": source_version,
        "source_ready": source_ready,
        "missing_requirements": missing_requirements,
        "has_active_agreement": has_active_agreement,
        "groq_enabled": runtime.provider is not None,
        "artifacts": artifacts,
    }


@workspace_router.post("/projects/{project_id}/assessments/{assessment_id}/reviews")
async def create_assessment_review(
    project_id: UUID,
    assessment_id: UUID,
    body: AssessmentReviewBody,
    principal=Depends(get_principal),
    runtime=Depends(get_runtime),
):
    """Issue a V4 assessment review receipt authorizing amendment draft generation."""
    source = await runtime.source(str(project_id), principal, write=True)
    if not source.agreement:
        raise IntegrationError("MISSING_AGREEMENT")

    artifact = await runtime.artifact(assessment_id, principal, "ASSESSMENT")
    if (
        artifact.source.project.project_id != str(project_id)
        or artifact.artifact_version != body.expected_version
        or artifact.content_digest != body.expected_digest
    ):
        raise IntegrationError("STALE_SOURCE")

    assessment = artifact.domain()
    if assessment.analysis.classification != "OUT_OF_SCOPE":
        raise IntegrationError("REVIEW_INVALID")

    reviewed = ReviewedAssessment(
        assessment_id=str(artifact.artifact_id),
        version=artifact.artifact_version,
        agreement_id=source.agreement.agreement_id,
        agreement_version=source.agreement.version,
        assessment=assessment,
    )
    agreement_digest = fingerprint(source.agreement)
    assessment_digest = fingerprint(reviewed)
    review_reference = f"cf-assess-rev-{uuid4()}"
    reviewed_at = datetime.now(timezone.utc)
    review_id = uuid4()

    async for conn in get_connection():
        await conn.execute(
            """
            INSERT INTO public.cf_assessment_reviews (
                assessment_review_id, review_reference, assessment_id, assessment_revision,
                original_agreement_id, original_agreement_version, agreement_digest, assessment_digest,
                reviewer_id, decision, verification_boundary, reviewed_at, revoked
            ) VALUES (
                $1, $2, $3, $4, $5::uuid, $6, $7, $8, $9::uuid,
                'AUTHORIZE_DRAFT_GENERATION', $10, $11, FALSE
            )
            """,
            review_id,
            review_reference,
            artifact.artifact_id,
            artifact.artifact_version,
            uuid.UUID(source.agreement.agreement_id),
            source.agreement.version,
            agreement_digest,
            assessment_digest,
            uuid.UUID(principal.user_id),
            runtime.assessment_reviews.boundary_reference,
            reviewed_at,
        )

    return {
        "assessment_review_id": str(review_id),
        "review_reference": review_reference,
        "assessment_id": str(artifact.artifact_id),
        "assessment_revision": artifact.artifact_version,
        "agreement_id": source.agreement.agreement_id,
        "agreement_version": source.agreement.version,
        "agreement_digest": agreement_digest,
        "assessment_digest": assessment_digest,
        "reviewer_id": principal.user_id,
        "decision": "AUTHORIZE_DRAFT_GENERATION",
        "reviewed_at": reviewed_at.isoformat(),
    }


@workspace_router.post("/amendments/{amendment_id}/reviews")
async def create_amendment_review(
    amendment_id: UUID,
    body: AmendmentReviewBody,
    principal=Depends(get_principal),
    runtime=Depends(get_runtime),
):
    """Issue a V5 amendment review grant after explicit human + semantic review confirmation."""
    artifact = await runtime.artifact(amendment_id, principal, "AMENDMENT")
    if artifact.artifact_version != body.expected_version or artifact.content_digest != body.expected_digest:
        raise IntegrationError("STALE_SOURCE")

    subject = ApprovalSubject.from_draft(artifact.domain(), artifact.artifact_version)
    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(hours=body.expires_in_hours)
    review_id = uuid4()

    async for conn in get_connection():
        await conn.execute(
            """
            INSERT INTO public.cf_reviews (
                review_id, amendment_id, revision, content_digest,
                reviewer_id, reviewed_at, expires_at,
                human_review, semantic_review, revoked
            ) VALUES ($1, $2, $3, $4, $5::uuid, $6, $7, TRUE, TRUE, FALSE)
            """,
            review_id,
            subject.amendment_id,
            subject.amendment_version,
            subject.content_digest,
            uuid.UUID(principal.user_id),
            now_utc,
            expires_at,
        )

    return {
        "review_id": str(review_id),
        "amendment_id": str(subject.amendment_id),
        "revision": subject.amendment_version,
        "content_digest": subject.content_digest,
        "reviewer_id": principal.user_id,
        "reviewed_at": now_utc.isoformat(),
        "expires_at": expires_at.isoformat(),
        "human_review": True,
        "semantic_review": True,
        "revoked": False,
    }


@workspace_router.post("/amendments/{amendment_id}/reviews/{review_id}/revoke")
async def revoke_amendment_review(
    amendment_id: UUID,
    review_id: UUID,
    body: RevokeReviewBody,
    principal=Depends(get_principal),
    runtime=Depends(get_runtime),
):
    """Revoke an active amendment review grant under exclusive row lock."""
    await runtime.artifact(amendment_id, principal, "AMENDMENT")

    async for conn in get_connection():
        row = await conn.fetchrow(
            "SELECT review_id FROM public.cf_reviews WHERE review_id = $1 AND amendment_id = $2",
            review_id,
            amendment_id,
        )
        if not row:
            raise IntegrationError("NOT_FOUND")

    await runtime.reviews.revoke(str(review_id), body.reason.strip(), principal.user_id)
    return {
        "review_id": str(review_id),
        "amendment_id": str(amendment_id),
        "revoked": True,
        "reason": body.reason.strip(),
    }
