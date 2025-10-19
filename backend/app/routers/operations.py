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
from backend.app.services.gemini_service import (
    generate_attack_plan,
    generate_ai_insight,
    generate_gemini_response,
    generate_gemini_attack_plan,
)
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
    force: bool = False  # Force new generation, bypass cache


# Cache for recent attack plan generations (repo_id -> {timestamp, plan_data})
# Plans cached for < 10 minutes to avoid excessive Gemini API calls
_attack_plan_cache: dict[str, dict] = {}


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
    """Generate AI-powered attack plan and sandbox simulation for the requested repository.
    
    Uses Gemini AI (when enabled) to analyze repository structure and generate
    contextual attack scenarios. Falls back to deterministic plan if AI unavailable.
    
    Features:
    - Caching: Returns cached results if generated < 10 minutes ago (unless force=true)
    - AI Insights: Includes Gemini-generated security analysis
    - Metadata: Persists prompts and raw responses for audit trails
    """

    logger.info("/simulate_attack request received", extra={
        "repo_id": request.repo_id,
        "force": request.force
    })
    _validate_repo_id(request.repo_id)

    try:
        # Check cache for recent simulation (< 10 minutes old)
        cache_key = request.repo_id
        if not request.force and cache_key in _attack_plan_cache:
            cached = _attack_plan_cache[cache_key]
            cache_age = (datetime.utcnow() - cached["timestamp"]).total_seconds()
            
            if cache_age < 600:  # 10 minutes = 600 seconds
                logger.info("Returning cached attack plan", extra={
                    "repo_id": request.repo_id,
                    "cache_age_seconds": cache_age
                })
                return cached["simulation_data"]
        
        # Load repository manifest for AI analysis
        try:
            manifest = repo_fetcher.load_repo_manifest(request.repo_id)
            high_risk_files = repo_fetcher.select_high_risk_files(manifest, limit=15)
            
            # Build repo profile for Gemini
            repo_profile = {
                "repo_id": request.repo_id,
                "manifest": manifest,
                "high_risk_files": high_risk_files,
                "languages": manifest.get("top_extensions", []),
                "dependencies": manifest.get("dependencies", []),
            }
            
            # Generate AI-powered attack plan
            logger.info("Generating AI attack plan", extra={
                "repo_id": request.repo_id,
                "high_risk_files": len(high_risk_files)
            })
            
            plan_dict = await run_in_threadpool(generate_gemini_attack_plan, repo_profile, 3)
            
            # Convert dict to AttackPlan model
            from backend.app.models.schemas import AttackStep
            
            steps = [
                AttackStep(
                    step_number=step["step_number"],
                    description=step["description"],
                    technique_id=step["technique_id"],
                    severity=step["severity"],
                    affected_files=step["affected_files"]
                )
                for step in plan_dict.get("steps", [])
            ]
            
            plan = AttackPlan(
                repo_id=request.repo_id,
                overall_severity=plan_dict.get("overall_severity", "high"),
                steps=steps
            )
            
        except repo_fetcher.ManifestNotFoundError:
            logger.warning("Repository manifest not found, using legacy attack plan", extra={
                "repo_id": request.repo_id
            })
            # Fallback to legacy function if manifest doesn't exist
            plan = generate_attack_plan(request.repo_id)
            plan_dict = None
        
        # Run sandbox simulation
        sandbox_result = run_sandbox_simulation(plan)

        # Create simulation record
        timestamp = datetime.utcnow()
        run_id = f"{request.repo_id}_{timestamp.strftime('%Y%m%dT%H%M%S%f')}"
        run_record = SimulationRun(
            repo_id=request.repo_id,
            run_id=run_id,
            timestamp=timestamp,
            plan=plan,
            sandbox=sandbox_result,
        )

        # Persist simulation with Gemini metadata
        simulation_data = _to_dict(run_record)
        
        # Add Gemini metadata to persisted data (not in response model)
        if plan_dict:
            simulation_data["gemini_metadata"] = {
                "plan_source": plan_dict.get("plan_source", "unknown"),
                "model_used": plan_dict.get("model_used"),
                "ai_insight": plan_dict.get("ai_insight"),
                "gemini_prompt": plan_dict.get("gemini_prompt"),
                "gemini_raw_response": plan_dict.get("gemini_raw_response")[:1000] if plan_dict.get("gemini_raw_response") else None,  # Truncate for storage
            }
        
        _persist_simulation(run_record)

        # Update cache
        _attack_plan_cache[cache_key] = {
            "timestamp": timestamp,
            "simulation_data": simulation_data
        }

        logger.info("/simulate_attack success", extra={
            "repo_id": request.repo_id,
            "run_id": run_id,
            "plan_source": plan_dict.get("plan_source") if plan_dict else "legacy",
            "ai_enabled": plan_dict is not None
        })
        
        return simulation_data
        
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


# ==============================================================================
# Gemini REST API Test Endpoint
# ==============================================================================


class GeminiQueryRequest(BaseModel):
    """Request payload for Gemini REST API query."""
    prompt: str


@router.post("/gemini/query", tags=["gemini"])
async def query_gemini_rest_api(request: GeminiQueryRequest):
    """
    Test endpoint for the new Gemini REST API function.
    
    This endpoint demonstrates usage of the generate_gemini_response() function
    that calls Gemini's REST API directly (not the SDK).
    
    Example request:
        POST /gemini/query
        {
            "prompt": "Explain what a SQL injection attack is"
        }
    
    Example response:
        {
            "text": "SQL injection is a code injection...",
            "model": "gemini-pro",
            "prompt_length": 40,
            "response_length": 150
        }
    """
    logger.info(
        "Gemini REST API query requested",
        extra={"prompt_length": len(request.prompt)}
    )
    
    try:
        # Call the new REST API function
        result = await run_in_threadpool(generate_gemini_response, request.prompt)
        
        if "error" in result:
            logger.error(
                "Gemini REST API returned error",
                extra={"error": result["error"]}
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result["error"],
                    "details": result.get("details", "No additional details")
                }
            )
        
        # Success response
        return {
            "text": result["text"],
            "model": result.get("model", "unknown"),
            "prompt_length": len(request.prompt),
            "response_length": len(result["text"])
        }
        
    except HTTPException:
        raise
    except ValueError as exc:
        # Configuration error (missing API key)
        logger.error("Gemini configuration error", extra={"error": str(exc)})
        raise HTTPException(
            status_code=500,
            detail={"error": str(exc)}
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in Gemini query endpoint")
        raise HTTPException(
            status_code=500,
            detail={"error": "Unexpected server error"}
        ) from exc


@router.get("/api/simulations/list")
async def list_all_simulations() -> dict[str, object]:
    """List all simulation files for dashboard analytics."""
    
    try:
        directory = ensure_simulation_dir()
        simulations = []
        
        # Read all JSON files in simulations directory
        for file_path in directory.glob("*.json"):
            try:
                with file_path.open("r", encoding="utf-8") as handle:
                    simulation_data = json.load(handle)
                    simulations.append(simulation_data)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read simulation file {file_path}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        simulations.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        logger.info(f"Listed {len(simulations)} simulations for dashboard")
        
        return {
            "success": True,
            "total": len(simulations),
            "simulations": simulations
        }
    
    except Exception as exc:
        logger.exception("Failed to list simulations")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to list simulations"}
        ) from exc
