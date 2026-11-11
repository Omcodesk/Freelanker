"""Export only; never mutate a teammate-owned FastAPI application."""

from uuid import UUID

from fastapi import APIRouter, Depends

from ..persistence.artifacts import StoredArtifact
from ..v5.schemas import ApprovalStatus, AuditEvent, DecisionRequest
from .dependencies import get_principal, get_runtime
from .errors import SafeRoute
from .schemas import ProjectRequest, AssessmentRequest, AmendmentRequest, RegisterRequest, DecisionBody

router = APIRouter(prefix="/api/v1/contractflow", tags=["ContractFlow"], route_class=SafeRoute)


@router.post("/contracts/generate", response_model=StoredArtifact)
async def contract(request: ProjectRequest, principal=Depends(get_principal), runtime=Depends(get_runtime)):
    return await runtime.generate("CONTRACT", request, principal)


@router.post("/agreements/draft", response_model=StoredArtifact)
async def agreement(request: ProjectRequest, principal=Depends(get_principal), runtime=Depends(get_runtime)):
    return await runtime.generate("AGREEMENT", request, principal)


@router.post("/scope/assess", response_model=StoredArtifact)
async def assess(request: AssessmentRequest, principal=Depends(get_principal), runtime=Depends(get_runtime)):
    return await runtime.generate("ASSESSMENT", request, principal)


@router.post("/amendments/generate", response_model=StoredArtifact)
async def amendment(request: AmendmentRequest, principal=Depends(get_principal), runtime=Depends(get_runtime)):
    return await runtime.generate("AMENDMENT", request, principal)


@router.post("/amendments/{amendment_id}/register", response_model=ApprovalStatus)
async def register(amendment_id: UUID, request: RegisterRequest, principal=Depends(get_principal), runtime=Depends(get_runtime)):
    return await runtime.register(amendment_id, request, principal)


@router.post("/amendments/{amendment_id}/decisions", response_model=ApprovalStatus)
async def decide(amendment_id: UUID, request: DecisionBody, principal=Depends(get_principal), runtime=Depends(get_runtime)):
    return await runtime.decision(DecisionRequest(amendment_id=amendment_id, **request.model_dump()), principal)


@router.get("/amendments/{amendment_id}/status", response_model=ApprovalStatus)
async def status(amendment_id: UUID, principal=Depends(get_principal), runtime=Depends(get_runtime)):
    return await runtime.read(amendment_id, principal)


@router.get("/amendments/{amendment_id}/history", response_model=tuple[AuditEvent, ...])
async def history(amendment_id: UUID, principal=Depends(get_principal), runtime=Depends(get_runtime)):
    return await runtime.read(amendment_id, principal, history=True)
