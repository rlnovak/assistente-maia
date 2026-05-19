from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models import FamilyProfile


def _build_profile_block(profile: "FamilyProfile | None") -> str:
    if profile is None:
        return ""
    has_data = any([profile.mother_name, profile.child_name, profile.child_age])
    if not has_data:
        return ""
    lines = []
    if profile.mother_name:
        lines.append(f"Nome da mãe: {profile.mother_name}")
    if profile.child_name:
        lines.append(f"Nome da criança: {profile.child_name}")
    if profile.child_age is not None:
        lines.append(f"Idade da criança: {profile.child_age} anos")
    return "\n".join(lines)


def get_system_prompt(provider: str | None = None, profile: "FamilyProfile | None" = None) -> str:
    provider = provider or settings.LLM_PROVIDER
    if provider == "anthropic":
        from app.llm.prompts.system_anthropic import build_system_prompt
        return build_system_prompt(_build_profile_block(profile))
    if provider == "openai":
        from app.llm.prompts.system_openai import build_system_prompt
        return build_system_prompt(_build_profile_block(profile))
    raise ValueError(f"Provider sem prompt definido: {provider}")