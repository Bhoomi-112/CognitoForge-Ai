"""API routers exposing core CognitoForge Labs functionality.

Payload cheat sheet for frontend devs:
- POST /upload_repo -> {"repo_id": str, "repo_url"?: str, "zip_file_base64"?: str}
- POST /simulate_attack -> {"repo_id": str}
- GET  /reports/{repo_id}/latest -> summary JSON with run_id + severity tallies
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from backend.app.core.settings import get_settings
from backend.app.models.schemas import (
    AttackPlan,
    RepoUpload,
    SimulationRun,
    SimulationReport,
    SimulationSummary,
    VulnerabilityReport,
)
from backend.app.services import repo_fetcher
from backend.app.services.gemini_service import generate_attack_plan, generate_ai_insight
from backend.app.services.sandbox_service import run_sandbox_simulation
from backend.app.services.snowflake_service import find_vulnerabilities_for_repo, list_all_vulnerabilities
from backend.app.utils.storage import (
    SimulationDataError,
    SimulationNotFoundError,
    ensure_simulation_dir,
    list_simulations,
    load_simulation,
)


class SimulateAttackRequest(BaseModel):
    """Request payload for generating an attack simulation."""

    repo_id: str


def _to_dict(model: BaseModel) -> dict[str, object]:
    """Return a plain dict regardless of Pydantic major version."""

    if hasattr(model, "model_dump"):
        return model.model_dump()  # Pydantic v2

    return model.dict()  # Pydantic v1 fallback


logger = logging.getLogger(__name__)

REPO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _persist_simulation(run: SimulationRun) -> None:
    """Persist the simulation payload as JSON so future requests can fetch it."""

    directory = ensure_simulation_dir()
    file_path = directory / f"{run.run_id}.json"
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(jsonable_encoder(run), handle, indent=2)


def _build_report(run: SimulationRun) -> SimulationReport:
    """Construct a report summary from a stored simulation run."""

    severity_counts = Counter(step.severity.lower() for step in run.plan.steps)
    summary = {
        "overall_severity": run.plan.overall_severity,
    }
    for severity, count in severity_counts.items():
        summary[f"{severity}_steps"] = count

    affected_files = sorted({file for step in run.plan.steps for file in step.affected_files})
    summary["affected_files"] = affected_files

    return SimulationReport(repo_id=run.repo_id, run_id=run.run_id, summary=summary)


async def _attach_ai_insight(run: SimulationRun, report: SimulationReport) -> Optional[str]:
    """Populate the report with an AI insight when Gemini is enabled."""

    settings = get_settings()
    if not settings.use_gemini:
        return None

    insight = await run_in_threadpool(generate_ai_insight, run, report)
    if insight:
        report.ai_insight = insight
    return insight


def _validate_repo_id(repo_id: str) -> None:
    """Ensure repository identifiers follow the expected pattern."""

    if not REPO_ID_PATTERN.fullmatch(repo_id):
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid repo_id. Use letters, numbers, underscores, or hyphens."},
        )


router = APIRouter(tags=["operations"])


@router.post("/upload_repo")
async def upload_repo(payload: RepoUpload) -> dict[str, object]:
    """Accept a repository upload request and return an acknowledgement."""

    logger.info("/upload_repo request received", extra={"repo_id": payload.repo_id})
    try:
        if not payload.repo_url and not payload.zip_file_base64:
            detail = {"error": "Either repo_url or zip_file_base64 must be provided"}
            logger.warning(
                "/upload_repo missing repo source",
                extra={"repo_id": payload.repo_id},
            )
            raise HTTPException(status_code=400, detail=detail)

        manifest_summary: Optional[dict[str, object]] = None
        if payload.repo_url:
            try:
                manifest_summary = repo_fetcher.fetch_and_store_repo(payload.repo_id, str(payload.repo_url))
            except repo_fetcher.RepoFetchError as exc:
                logger.exception(
                    "/upload_repo repository fetch failed",
                    extra={"repo_id": payload.repo_id, "repo_url": str(payload.repo_url)},
                )
                raise HTTPException(status_code=502, detail={"error": str(exc)}) from exc

        response = {
            "repo_id": payload.repo_id,
            "status": "ingested",
            "source": "url" if payload.repo_url else "upload",
        }
        if manifest_summary:
            response["files_indexed"] = manifest_summary.get("file_count")
            response["high_risk_files"] = manifest_summary.get("high_risk_file_count")
        logger.info("/upload_repo success", extra={"repo_id": payload.repo_id})
        return response
    except HTTPException:
        logger.exception("/upload_repo failed", extra={"repo_id": payload.repo_id})
        raise
    except Exception as exc:
        logger.exception("Unexpected error during /upload_repo", extra={"repo_id": payload.repo_id})
        raise HTTPException(status_code=500, detail={"error": "Unexpected server error"}) from exc


@router.post("/simulate_attack", response_model=SimulationRun)
async def simulate_attack(request: SimulateAttackRequest) -> dict[str, object]:
    """Return a mock attack plan and sandbox execution log for the requested repository."""

    logger.info("/simulate_attack request received", extra={"repo_id": request.repo_id})
    _validate_repo_id(request.repo_id)

    try:
        plan: AttackPlan = generate_attack_plan(request.repo_id)
        sandbox_result = run_sandbox_simulation(plan)

        timestamp = datetime.utcnow()
        run_id = f"{request.repo_id}_{timestamp.strftime('%Y%m%dT%H%M%S%f')}"
        run_record = SimulationRun(
            repo_id=request.repo_id,
            run_id=run_id,
            timestamp=timestamp,
            plan=plan,
            sandbox=sandbox_result,
        )

        _persist_simulation(run_record)  # Persistence hook sits here so future endpoints can read it back.

        logger.info("/simulate_attack success", extra={"repo_id": request.repo_id, "run_id": run_id})
        return _to_dict(run_record)
    except HTTPException:
        logger.exception("/simulate_attack failed", extra={"repo_id": request.repo_id})
        raise
    except Exception as exc:
        logger.exception("Unexpected error during /simulate_attack", extra={"repo_id": request.repo_id})
        raise HTTPException(status_code=500, detail={"error": "Unexpected server error"}) from exc


@router.get("/fetch_report")
async def fetch_report(repo_id: str) -> dict[str, object]:
    """Produce a vulnerability report for the supplied repository."""

    logger.info("/fetch_report request received", extra={"repo_id": repo_id})
    try:
        findings = find_vulnerabilities_for_repo(repo_id)
        if not findings:
            findings = list_all_vulnerabilities()

        report = VulnerabilityReport(repo_id=repo_id, findings=findings)
        logger.info("/fetch_report success", extra={"repo_id": repo_id, "finding_count": len(findings)})
        return _to_dict(report)
    except HTTPException:
        logger.exception("/fetch_report failed", extra={"repo_id": repo_id})
        raise
    except Exception as exc:
        logger.exception("Unexpected error during /fetch_report", extra={"repo_id": repo_id})
        raise HTTPException(status_code=500, detail={"error": "Unexpected server error"}) from exc


@router.get("/simulations/{repo_id}", response_model=List[SimulationSummary])
async def list_simulations_endpoint(repo_id: str) -> List[dict[str, object]]:
    """Return summaries of every stored simulation for the repository."""

    logger.info("/simulations list request received", extra={"repo_id": repo_id})
    _validate_repo_id(repo_id)
    try:
        summaries = list_simulations(repo_id)
        logger.info(
            "/simulations list success",
            extra={"repo_id": repo_id, "count": len(summaries)},
        )
        return [_to_dict(summary) for summary in summaries]
    except SimulationDataError as exc:
        logger.exception("/simulations list data error", extra={"repo_id": repo_id})
        return JSONResponse(status_code=500, content={"error": str(exc)})
    except HTTPException:
        logger.exception("/simulations list failed", extra={"repo_id": repo_id})
        raise
    except Exception as exc:
        logger.exception("Unexpected error listing simulations", extra={"repo_id": repo_id})
        raise HTTPException(status_code=500, detail={"error": "Unexpected server error"}) from exc


@router.get("/reports/{repo_id}/latest", response_model=SimulationReport)
async def get_latest_simulation_report(repo_id: str) -> dict[str, object]:
    """Fetch the most recent simulation run and return its summary report."""

    logger.info("/reports latest request received", extra={"repo_id": repo_id})
    _validate_repo_id(repo_id)
    try:
        summaries = list_simulations(repo_id)
        if not summaries:
            logger.warning("/reports latest not found", extra={"repo_id": repo_id})
            raise HTTPException(status_code=404, detail={"error": f"No simulations found for {repo_id}"})

        summaries.sort(key=lambda item: item.timestamp, reverse=True)
        latest_summary = summaries[0]
        logger.info(
            "/reports latest selecting run",
            extra={"repo_id": repo_id, "run_id": latest_summary.run_id},
        )

        run = load_simulation(repo_id, latest_summary.run_id)
        report = _build_report(run)
        insight = await _attach_ai_insight(run, report)
        logger.info(
            "/reports latest success",
            extra={
                "repo_id": repo_id,
                "run_id": latest_summary.run_id,
                "ai_insight_present": bool(insight),
            },
        )
        return _to_dict(report)
    except SimulationNotFoundError as exc:
        logger.warning("/reports latest run missing", extra={"repo_id": repo_id})
        raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc
    except SimulationDataError as exc:
        logger.exception("/reports latest data error", extra={"repo_id": repo_id})
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc
    except HTTPException:
        logger.exception("/reports latest failed", extra={"repo_id": repo_id})
        raise
    except Exception as exc:
        logger.exception("Unexpected error retrieving latest simulation report", extra={"repo_id": repo_id})
        raise HTTPException(status_code=500, detail={"error": "Unexpected server error"}) from exc


@router.get("/simulations/{repo_id}/{run_id}", response_model=SimulationRun)
async def get_simulation(repo_id: str, run_id: str) -> dict[str, object]:
    """Return the persisted simulation payload for the requested run identifier."""

    logger.info("/simulations detail request received", extra={"repo_id": repo_id, "run_id": run_id})
    _validate_repo_id(repo_id)
    try:
        run = load_simulation(repo_id, run_id)
        logger.info("/simulations detail success", extra={"repo_id": repo_id, "run_id": run_id})
        return _to_dict(run)
    except SimulationNotFoundError as exc:
        logger.warning(
            "/simulations detail not found",
            extra={"repo_id": repo_id, "run_id": run_id},
        )
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except SimulationDataError as exc:
        logger.exception(
            "/simulations detail data error",
            extra={"repo_id": repo_id, "run_id": run_id},
        )
        return JSONResponse(status_code=500, content={"error": str(exc)})
    except HTTPException:
        logger.exception(
            "/simulations detail failed",
            extra={"repo_id": repo_id, "run_id": run_id},
        )
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected error retrieving simulation detail",
            extra={"repo_id": repo_id, "run_id": run_id},
        )
        raise HTTPException(status_code=500, detail={"error": "Unexpected server error"}) from exc


@router.get("/reports/{repo_id}/{run_id}", response_model=SimulationReport)
async def get_simulation_report(repo_id: str, run_id: str) -> dict[str, object]:
    """Produce a structured summary of a persisted simulation run."""

    logger.info("/reports detail request received", extra={"repo_id": repo_id, "run_id": run_id})
    _validate_repo_id(repo_id)
    try:
        run = load_simulation(repo_id, run_id)
        report = _build_report(run)
        insight = await _attach_ai_insight(run, report)
        logger.info(
            "/reports detail success",
            extra={
                "repo_id": repo_id,
                "run_id": run_id,
                "ai_insight_present": bool(insight),
            },
        )
        return _to_dict(report)
    except SimulationNotFoundError as exc:
        logger.warning(
            "/reports detail not found",
            extra={"repo_id": repo_id, "run_id": run_id},
        )
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except SimulationDataError as exc:
        logger.exception(
            "/reports detail data error",
            extra={"repo_id": repo_id, "run_id": run_id},
        )
        return JSONResponse(status_code=500, content={"error": str(exc)})
    except HTTPException:
        logger.exception(
            "/reports detail failed",
            extra={"repo_id": repo_id, "run_id": run_id},
        )
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected error retrieving simulation report",
            extra={"repo_id": repo_id, "run_id": run_id},
        )
        raise HTTPException(status_code=500, detail={"error": "Unexpected server error"}) from exc
