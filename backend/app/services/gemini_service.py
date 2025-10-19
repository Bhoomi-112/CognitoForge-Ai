"""Google Gemini helpers for attack planning and report summarisation."""

from __future__ import annotations

import importlib
import json
import logging
import re
import textwrap
from typing import Dict, List, Optional

import httpx

from backend.app.core.settings import get_settings
from backend.app.models.schemas import AttackPlan, AttackStep, SimulationReport, SimulationRun
from backend.app.services import repo_fetcher

logger = logging.getLogger(__name__)

_FALLBACK_MESSAGE = "Gemini unavailable"
_ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}
_DEFAULT_OVERALL_SEVERITY = "high"


class GeminiPlanError(RuntimeError):
    """Raised when Gemini cannot produce a valid attack plan."""


def generate_attack_plan(repo_id: str) -> AttackPlan:
    """Generate an attack plan for ``repo_id`` using Gemini when available."""

    settings = get_settings()

    manifest: Optional[Dict[str, object]] = None
    try:
        manifest = repo_fetcher.load_repo_manifest(repo_id)
    except repo_fetcher.ManifestNotFoundError:
        logger.warning("Repository manifest not found; defaulting to mock plan", extra={"repo_id": repo_id})

    if settings.use_gemini and settings.gemini_api_key and manifest:
        try:
            plan = _generate_plan_with_gemini(repo_id, manifest)
            logger.info(
                "Gemini attack plan generated",
                extra={"repo_id": repo_id, "steps": len(plan.steps)},
            )
            return plan
        except GeminiPlanError as exc:
            logger.warning(
                "Falling back to default attack plan after Gemini failure",
                extra={"repo_id": repo_id, "error": str(exc)},
            )
    else:
        logger.debug(
            "Using default attack plan",
            extra={
                "repo_id": repo_id,
                "use_gemini": settings.use_gemini,
                "manifest_available": bool(manifest),
            },
        )

    return _build_default_plan(repo_id)


def _build_default_plan(repo_id: str) -> AttackPlan:
    """Return the historical static attack plan used as a fallback."""

    steps: List[AttackStep] = [
        AttackStep(
            step_number=1,
            description="Initial access via exposed CI token in repository secrets.",
            technique_id="T1552",
            severity="high",
            affected_files=[".github/workflows/deploy.yml"],
        ),
        AttackStep(
            step_number=2,
            description="Privilege escalation through misconfigured Kubernetes RBAC manifests.",
            technique_id="T1068",
            severity="critical",
            affected_files=["deploy/k8s/rbac.yaml"],
        ),
        AttackStep(
            step_number=3,
            description="Establish persistence by modifying container entrypoint script.",
            technique_id="T1547",
            severity="medium",
            affected_files=["docker/entrypoint.sh"],
        ),
    ]

    return AttackPlan(repo_id=repo_id, overall_severity="critical", steps=steps)


def _generate_plan_with_gemini(repo_id: str, manifest: Dict[str, object]) -> AttackPlan:
    """Use Gemini to craft an attack plan based on the repository manifest."""

    high_risk_files = repo_fetcher.select_high_risk_files(manifest, limit=10)
    if not high_risk_files:
        raise GeminiPlanError("Manifest did not expose any high-risk files to analyse")

    prompt = _build_plan_prompt(repo_id, manifest, high_risk_files)
    logger.debug(
        "Gemini attack plan prompt prepared",
        extra={
            "repo_id": repo_id,
            "high_risk_file_count": len(high_risk_files),
        },
    )

    response_text = _invoke_gemini(prompt, {"repo_id": repo_id, "mode": "attack_plan"})
    plan_payload = _parse_plan_json(response_text)
    return _plan_from_dict(repo_id, plan_payload, manifest, high_risk_files)


def _build_plan_prompt(
    repo_id: str,
    manifest: Dict[str, object],
    high_risk_files: List[Dict[str, object]],
) -> str:
    """Create the prompt instructing Gemini to return a JSON attack plan."""

    manifest_summary = {
        "file_count": manifest.get("file_count"),
        "high_risk_file_count": manifest.get("high_risk_file_count"),
        "top_extensions": manifest.get("top_extensions", []),
    }
    high_risk_payload = [
        {
            "path": file.get("path"),
            "risk_level": file.get("risk_level"),
            "risk_reasons": file.get("risk_reasons", []),
            "size": file.get("size"),
        }
        for file in high_risk_files
        if file.get("path")
    ]

    format_instructions = {
        "overall_severity": "one of: low, medium, high, critical",
        "steps": [
            {
                "step_number": "int starting at 1",
                "description": "one sentence summarising attacker action",
                "technique_id": "MITRE ATT&CK ID (e.g. T1552)",
                "severity": "one of: low, medium, high, critical",
                "affected_files": "array of file paths chosen from the provided list",
            }
        ],
    }

    prompt = textwrap.dedent(
        f"""
        You are an experienced adversarial security engineer reviewing the repository below. Identify exploitable attack steps that a red team would attempt, prioritising files that are most likely to contain secrets, CI/CD misconfigurations, or insecure infrastructure as code.

        Repository ID: {repo_id}
        Repository summary (JSON):
        {json.dumps(manifest_summary, indent=2)}

        High risk files (JSON array):
        {json.dumps(high_risk_payload, indent=2)}

        Produce up to three attack steps that are realistic, actionable, and reference only the files listed. Each step must:
          - describe the attacker action in one sentence,
          - map to a MITRE ATT&CK technique id,
          - grade severity (low/medium/high/critical),
          - list the impacted files using repository paths provided above.

        Respond ONLY with JSON matching this structure:
        {json.dumps(format_instructions, indent=2)}
        """
    ).strip()

    return prompt


def _invoke_gemini(prompt: str, log_extra: Dict[str, object]) -> str:
    """Call the Gemini API and return the textual response."""

    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiPlanError("Gemini API key is not configured")

    try:
        genai = importlib.import_module("google.generativeai")
    except ImportError as exc:
        raise GeminiPlanError("google-generativeai package is not installed") from exc

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
        logger.info(
            "Requesting Gemini content",
            extra={**log_extra, "model": settings.gemini_model},
        )
        response = model.generate_content(prompt)
    except Exception as exc:  # noqa: BLE001
        raise GeminiPlanError("Gemini API request failed") from exc

    text = _extract_text_from_response(response)
    if not text:
        raise GeminiPlanError("Gemini response did not contain text output")
    return text


_JSON_BLOCK_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _parse_plan_json(raw_text: str) -> Dict[str, object]:
    """Extract a JSON object from Gemini's response text."""

    if not raw_text:
        raise GeminiPlanError("Empty response received from Gemini")

    candidates = []
    code_block_pattern = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
    candidates.extend(code_block_pattern.findall(raw_text))
    candidates.append(raw_text)

    for candidate in candidates:
        snippet = candidate.strip()
        if not snippet:
            continue
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            continue

    match = _JSON_BLOCK_PATTERN.search(raw_text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise GeminiPlanError("Unable to decode JSON from Gemini response") from exc

    raise GeminiPlanError("Could not parse JSON from Gemini response")


def _plan_from_dict(
    repo_id: str,
    plan_payload: Dict[str, object],
    manifest: Dict[str, object],
    high_risk_files: List[Dict[str, object]],
) -> AttackPlan:
    """Convert Gemini JSON payload into an ``AttackPlan`` object."""

    steps_payload = plan_payload.get("steps")
    if not isinstance(steps_payload, list) or not steps_payload:
        raise GeminiPlanError("Gemini response did not include any attack steps")

    valid_paths = set(repo_fetcher.list_all_paths(manifest))
    high_risk_paths = [file.get("path") for file in high_risk_files if file.get("path")]

    steps: List[AttackStep] = []
    for index, raw_step in enumerate(steps_payload[:3], start=1):
        if not isinstance(raw_step, dict):
            continue

        description = str(raw_step.get("description") or "").strip()
        technique_id = _normalise_technique_id(raw_step.get("technique_id"))
        severity = _normalise_severity(raw_step.get("severity"))

        affected_files_raw = raw_step.get("affected_files") or []
        if isinstance(affected_files_raw, str):
            affected_files_raw = [affected_files_raw]
        filtered_files = [path for path in affected_files_raw if path in valid_paths]
        if not filtered_files and high_risk_paths:
            filtered_files = [high_risk_paths[min(index - 1, len(high_risk_paths) - 1)]]

        if not description:
            continue

        steps.append(
            AttackStep(
                step_number=int(raw_step.get("step_number") or index),
                description=description,
                technique_id=technique_id,
                severity=severity,
                affected_files=filtered_files,
            )
        )

    if not steps:
        raise GeminiPlanError("No valid attack steps could be derived from Gemini response")

    overall = _normalise_severity(plan_payload.get("overall_severity"))
    return AttackPlan(repo_id=repo_id, overall_severity=overall, steps=steps)


def _normalise_severity(value: Optional[object]) -> str:
    """Return a severity string limited to the allowed set."""

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _ALLOWED_SEVERITIES:
            return lowered
    return _DEFAULT_OVERALL_SEVERITY


def _normalise_technique_id(value: Optional[object]) -> str:
    """Return a best-effort MITRE technique id."""

    if isinstance(value, str) and value.strip():
        candidate = value.strip().upper()
        if not candidate.startswith("T"):
            candidate = f"T{candidate}"
        return candidate
    return "T0000"


def _extract_text_from_response(response: object) -> Optional[str]:
    """Best-effort extraction of textual content from a Gemini response object."""

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    parts: List[str] = []
    candidates = getattr(response, "candidates", []) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            if hasattr(part, "text") and isinstance(part.text, str) and part.text.strip():
                parts.append(part.text.strip())

    if parts:
        return "\n".join(parts).strip()

    return None


def _build_insight_prompt(run: SimulationRun, report: SimulationReport) -> str:
    """Create a prompt for Gemini that summarises the simulation context."""

    severity_breakdown = {
        key: value for key, value in report.summary.items() if key.endswith("_steps")
    }
    affected_files = report.summary.get("affected_files", [])
    step_lines = []
    for step in run.plan.steps:
        files = ", ".join(step.affected_files) if step.affected_files else "None specified"
        step_lines.append(
            f"Step {step.step_number}: {step.description} | Severity: {step.severity} | Technique: {step.technique_id} | Files: {files}"
        )
    step_section = "\n".join(step_lines) if step_lines else "No attack steps were captured."

    sandbox_summary = ""
    if isinstance(run.sandbox, dict):
        sandbox_summary = run.sandbox.get("summary") or "Sandbox summary unavailable."
        logs = run.sandbox.get("logs") or []
        log_lines = []
        for entry in logs[:5]:
            timestamp = entry.get("timestamp", "?")
            action = entry.get("action", "unknown action")
            status = entry.get("status", "unknown status")
            step = entry.get("step", "?")
            log_lines.append(f"- [{timestamp}] Step {step}: {action} -> {status}")
        log_section = "\n".join(log_lines) if log_lines else "No sandbox log entries supplied."
    else:
        sandbox_summary = "Sandbox summary unavailable."
        log_section = "No sandbox log entries supplied."

    prompt = textwrap.dedent(
        f"""
        You are an experienced DevSecOps analyst. Review the simulated attack below and provide a concise AI insight (no more than three sentences) highlighting key risks and suggested focus areas for remediation. Avoid repeating the raw data verbatim.

        Repository: {run.repo_id}
        Simulation Run: {run.run_id}
        Overall Severity: {report.summary.get('overall_severity', 'unknown')}
        Severity Breakdown: {severity_breakdown}
        Affected Files: {', '.join(affected_files) if affected_files else 'None listed'}

        Attack Plan Steps:
        {step_section}

        Sandbox Summary:
        {sandbox_summary}

        Sandbox Log Sample:
        {log_section}

        Provide the AI Insight as a short paragraph ready for display to security engineers.
        """
    ).strip()

    return prompt


def generate_ai_insight(run: SimulationRun, report: SimulationReport) -> Optional[str]:
    """Generate a short Gemini-produced insight for a simulation run."""

    settings = get_settings()
    if not settings.use_gemini:
        logger.debug(
            "Gemini insight generation skipped because USE_GEMINI is disabled",
            extra={"repo_id": run.repo_id, "run_id": run.run_id},
        )
        return None

    if not settings.gemini_api_key:
        logger.warning(
            "Gemini enabled but API key not configured",
            extra={"repo_id": run.repo_id, "run_id": run.run_id},
        )
        return _FALLBACK_MESSAGE

    prompt = _build_insight_prompt(run, report)

    try:
        insight_text = _invoke_gemini(
            prompt,
            {
                "repo_id": run.repo_id,
                "run_id": run.run_id,
                "mode": "insight",
            },
        )
        logger.info(
            "Gemini insight generated",
            extra={
                "repo_id": run.repo_id,
                "run_id": run.run_id,
                "model": settings.gemini_model,
                "characters": len(insight_text),
            },
        )
        return insight_text
    except GeminiPlanError as exc:
        logger.exception(
            "Gemini insight generation failed",
            extra={"repo_id": run.repo_id, "run_id": run.run_id, "error": str(exc)},
        )
        return _FALLBACK_MESSAGE


# ==============================================================================
# REST API Interface
# ==============================================================================


def generate_gemini_response(prompt: str) -> dict:
    """
    Generate a response from Gemini using the REST API.
    
    This function provides direct access to the Gemini API via HTTP requests,
    as an alternative to the google-generativeai SDK used elsewhere.
    
    Args:
        prompt: The text prompt to send to Gemini
        
    Returns:
        dict: Response containing 'text' key with the model's output,
              or 'error' key if the request failed
              
    Example:
        >>> result = generate_gemini_response("Explain what a SQL injection is")
        >>> print(result['text'])
        
    Raises:
        ValueError: If GEMINI_API_KEY is not configured
        httpx.TimeoutException: If the request times out
        httpx.HTTPError: If the HTTP request fails
    """
    settings = get_settings()
    
    # Validate configuration
    if not settings.gemini_api_key:
        error_msg = "GEMINI_API_KEY environment variable is not configured"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Use configured model or default to gemini-pro
    model_name = settings.gemini_model or "gemini-pro"
    
    # Use v1beta for broader model support
    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        f"?key={settings.gemini_api_key}"
    )
    
    # Build request payload
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    logger.info(
        "Sending Gemini REST API request",
        extra={
            "model": model_name,
            "prompt_length": len(prompt),
            "api_method": "REST"
        }
    )
    
    try:
        # Make HTTP request with timeout
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # Extract text from response
            if "candidates" in response_data and len(response_data["candidates"]) > 0:
                candidate = response_data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        text_output = parts[0]["text"]
                        
                        logger.info(
                            "Gemini REST API response received",
                            extra={
                                "model": model_name,
                                "response_length": len(text_output),
                                "candidates": len(response_data["candidates"])
                            }
                        )
                        
                        return {
                            "text": text_output,
                            "model": model_name,
                            "candidates": response_data.get("candidates", [])
                        }
            
            # Response doesn't contain expected structure
            error_msg = "Gemini response did not contain expected text output"
            logger.warning(
                error_msg,
                extra={"response_structure": list(response_data.keys())}
            )
            return {
                "error": error_msg,
                "raw_response": response_data
            }
            
    except httpx.TimeoutException as exc:
        error_msg = "Gemini API request timed out after 30 seconds"
        logger.error(
            error_msg,
            extra={"model": model_name, "error": str(exc)}
        )
        return {
            "error": error_msg,
            "exception": str(exc)
        }
        
    except httpx.HTTPStatusError as exc:
        error_msg = f"Gemini API returned HTTP {exc.response.status_code}"
        logger.error(
            error_msg,
            extra={
                "model": model_name,
                "status_code": exc.response.status_code,
                "response_text": exc.response.text[:500]  # Log first 500 chars
            }
        )
        return {
            "error": error_msg,
            "status_code": exc.response.status_code,
            "details": exc.response.text
        }
        
    except httpx.HTTPError as exc:
        error_msg = f"HTTP error occurred: {type(exc).__name__}"
        logger.exception(
            "Gemini API HTTP request failed",
            extra={"model": model_name, "error": str(exc)}
        )
        return {
            "error": error_msg,
            "exception": str(exc)
        }
        
    except json.JSONDecodeError as exc:
        error_msg = "Failed to parse Gemini API response as JSON"
        logger.exception(
            error_msg,
            extra={"model": model_name, "error": str(exc)}
        )
        return {
            "error": error_msg,
            "exception": str(exc)
        }
        
    except Exception as exc:  # noqa: BLE001
        error_msg = f"Unexpected error calling Gemini API: {type(exc).__name__}"
        logger.exception(
            "Unexpected Gemini API error",
            extra={"model": model_name, "error": str(exc)}
        )
        return {
            "error": error_msg,
            "exception": str(exc)
        }
