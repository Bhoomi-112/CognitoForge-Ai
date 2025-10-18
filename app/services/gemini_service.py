"""Stub integration with Google Gemini for attack plan generation."""

from __future__ import annotations

from typing import List

from app.core.settings import get_settings
from app.models.schemas import AttackPlan, AttackStep


def generate_attack_plan(repo_id: str) -> AttackPlan:
    """Build a mock attack plan that would normally come from Gemini responses."""

    settings = get_settings()
    # The Gemini API key is not used in this stub but the check documents where it will matter.
    if not settings.gemini_api_key:
        # Keeping an explicit branch helps future developers wire the real integration.
        pass

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
