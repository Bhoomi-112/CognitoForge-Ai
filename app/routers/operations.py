"""API routers exposing core CognitoForge Labs functionality."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import AttackPlan, RepoUpload, VulnerabilityReport
from app.services.gemini_service import generate_attack_plan
from app.services.sandbox_service import run_sandbox_simulation
from app.services.snowflake_service import find_vulnerabilities_for_repo, list_all_vulnerabilities


class SimulateAttackRequest(BaseModel):
    """Request payload for generating an attack simulation."""

    repo_id: str


def _to_dict(model: BaseModel) -> dict[str, object]:
    """Return a plain dict regardless of Pydantic major version."""

    if hasattr(model, "model_dump"):
        return model.model_dump()  # Pydantic v2

    return model.dict()  # Pydantic v1 fallback


router = APIRouter(tags=["operations"])


@router.post("/upload_repo")
async def upload_repo(payload: RepoUpload) -> dict[str, str]:
    """Accept a repository upload request and return an acknowledgement."""

    if not payload.repo_url and not payload.zip_file_base64:
        raise HTTPException(status_code=400, detail="Either repo_url or zip_file_base64 must be provided")

    return {
        "repo_id": payload.repo_id,
        "status": "ingested",
        "source": "url" if payload.repo_url else "upload",
    }


@router.post("/simulate_attack")
async def simulate_attack(request: SimulateAttackRequest) -> dict[str, object]:
    """Return a mock attack plan and sandbox execution log for the requested repository."""

    plan: AttackPlan = generate_attack_plan(request.repo_id)
    sandbox_result = run_sandbox_simulation(plan)
    return {
        "plan": _to_dict(plan),
        "sandbox": sandbox_result,
    }


@router.get("/fetch_report")
async def fetch_report(repo_id: str) -> dict[str, object]:
    """Produce a vulnerability report for the supplied repository."""

    findings = find_vulnerabilities_for_repo(repo_id)
    if not findings:
        findings = list_all_vulnerabilities()

    report = VulnerabilityReport(repo_id=repo_id, findings=findings)
    return _to_dict(report)
