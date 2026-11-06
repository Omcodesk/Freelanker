import asyncio
import math
from uuid import uuid4

from pydantic import ValidationError

from ..errors import GenerationTimeout, InvalidProviderOutput
from ..providers.base import ContractProvider
from .provider_errors import categorize_provider_error
from .errors import AmendmentValidationError, ReviewVerificationError
from .prompts import build_prompts
from .renderer import render_text
from .review import ReviewVerifier, validate_receipt
from .schemas import AmendmentDraft, AmendmentRequest, AmendmentWording, VerifiedReview
from .validation import validate_wording
from .diagnostics import schema_diagnostics


class AmendmentDraftService:
    def __init__(self, provider: ContractProvider, review_verifier: ReviewVerifier, *, timeout_seconds=30):
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 300:
            raise ValueError("Timeout must be finite, positive and <= 300 seconds")
        self.provider, self.review_verifier, self.timeout_seconds = provider, review_verifier, timeout_seconds

    async def generate_amendment(self, request) -> AmendmentDraft:
        payload = request.model_dump() if isinstance(request, AmendmentRequest) else request
        initial = AmendmentRequest.model_validate(payload)
        snapshot = AmendmentRequest.model_validate_json(initial.model_dump_json())
        try:
            async with asyncio.timeout(self.timeout_seconds):
                receipt = await self.review_verifier.verify_review(snapshot.review_reference)
                record = VerifiedReview.model_validate_json(receipt.model_dump_json())
                validate_receipt(snapshot, record, self.review_verifier.boundary_reference)
        except TimeoutError:
            raise GenerationTimeout("Review verification timed out") from None
        except Exception:
            raise ReviewVerificationError("Trusted current review could not be verified") from None
        system, user = build_prompts(snapshot)
        try:
            async with asyncio.timeout(self.timeout_seconds):
                raw = await self.provider.generate(system_prompt=system, user_prompt=user)
        except TimeoutError:
            raise GenerationTimeout("Amendment generation timed out") from None
        except InvalidProviderOutput:
            raise AmendmentValidationError(check="PROVIDER_INCOMPLETE_OUTPUT", field=("response",)) from None
        except Exception as error:
            raise categorize_provider_error(error) from None
        try:
            if not isinstance(raw, str):
                raise AmendmentValidationError(check="RESPONSE_TYPE", field=("response",))
            if len(raw.encode()) > 64000:
                raise AmendmentValidationError(check="RESPONSE_SIZE", field=("response",))
            wording = AmendmentWording.model_validate_json(raw)
            validate_wording(snapshot, wording)
            draft_id = uuid4()
            a, r = snapshot.original_agreement, snapshot.reviewed_assessment
            draft = AmendmentDraft(draft_id=draft_id, original_agreement_id=a.agreement_id,
                                   original_agreement_version=a.version, project_id=a.project.project_id,
                                   assessment_id=r.assessment_id, assessment_version=r.version, original_facts=a.project,
                                   request_snapshot=snapshot, verified_review=record,
                                   proposals=wording, rendered_text=render_text(draft_id, snapshot, wording))
            return AmendmentDraft.model_validate_json(draft.model_dump_json())
        except AmendmentValidationError:
            raise
        except ValidationError as error:
            raise AmendmentValidationError(diagnostics=schema_diagnostics(error)) from None
        except (ValueError, TypeError):
            raise AmendmentValidationError() from None
