"""Stub integration with Google Gemini for attack plan generation."""

from __future__ import annotations

import logging
from typing import List

from backend.app.core.settings import get_settings
from backend.app.models.schemas import AttackPlan, AttackStep

logger = logging.getLogger(__name__)


def generate_attack_plan(repo_id: str) -> AttackPlan:
    """Build a mock attack plan that would normally come from Gemini responses."""

    settings = get_settings()
    if settings.use_gemini and settings.gemini_api_key:
        # TODO: Replace this stub with a real Gemini API call once the integration contract is finalised.
        logger.info("USE_GEMINI enabled but real integration is pending; returning mock plan", extra={"repo_id": repo_id})
    else:
        logger.debug("Returning mock Gemini attack plan", extra={"repo_id": repo_id})

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
