import re
from uuid import UUID

from app.core.logging import get_logger
from app.db.models import FamilyProfile, FamilyProfileUpdate
from app.db.supabase import get_supabase_client

log = get_logger(__name__)

_AGE_PATTERN = re.compile(
    r'\b(\d{1,2})\s*(?:ano[s]?|mês(?:es)?|month[s]?|year[s]?)\b',
    re.IGNORECASE,
)
_NAME_INDICATORS = [
    r'meu\s+filho\s+(?:se\s+chama\s+|é\s+(?:o\s+)?|)\s*([A-ZÁÉÍÓÚÃÕÇÀÈÌ][a-záéíóúãõçàèì]+)',
    r'minha\s+filha\s+(?:se\s+chama\s+|é\s+(?:a\s+)?|)\s*([A-ZÁÉÍÓÚÃÕÇÀÈÌ][a-záéíóúãõçàèì]+)',
    r'(?:chama|chamamos|nome\s+é|nome\s+dele|nome\s+dela)\s+(?:é\s+)?([A-ZÁÉÍÓÚÃÕÇÀÈÌ][a-záéíóúãõçàèì]+)',
    r'(?:meu\s+nome\s+é|me\s+chamo|sou\s+a?)\s+([A-ZÁÉÍÓÚÃÕÇÀÈÌ][a-záéíóúãõçàèì]+)',
]


def get_or_create_profile(user_id: UUID) -> FamilyProfile:
    client = get_supabase_client()
    result = (
        client.table("user_family_profiles")
        .select("*")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if result.data:
        return FamilyProfile(**result.data[0])

    insert = (
        client.table("user_family_profiles")
        .insert({"user_id": str(user_id)})
        .execute()
    )
    return FamilyProfile(**insert.data[0])


def update_profile(user_id: UUID, data: FamilyProfileUpdate) -> FamilyProfile:
    client = get_supabase_client()
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if not payload:
        return get_or_create_profile(user_id)

    result = (
        client.table("user_family_profiles")
        .update(payload)
        .eq("user_id", str(user_id))
        .execute()
    )
    if result.data:
        return FamilyProfile(**result.data[0])
    return get_or_create_profile(user_id)


def extract_and_update_profile(user_id: UUID, message: str) -> None:
    """Extrai nome/idade da mensagem e faz upsert incremental (não sobrescreve campos já preenchidos)."""
    try:
        profile = get_or_create_profile(user_id)
        updates: dict = {}

        if not profile.child_age:
            match = _AGE_PATTERN.search(message)
            if match:
                age = int(match.group(1))
                if 0 <= age <= 12:
                    updates["child_age"] = age

        if not profile.child_name or not profile.mother_name:
            for pattern in _NAME_INDICATORS:
                m = re.search(pattern, message, re.IGNORECASE)
                if m:
                    name = m.group(1).strip()
                    if len(name) >= 2:
                        # heurística simples: se detectamos meu/minha filho/filha → child_name, senão mother_name
                        if re.search(r'filho|filha|criança|bebê', pattern, re.IGNORECASE):
                            if not profile.child_name:
                                updates["child_name"] = name
                        else:
                            if not profile.mother_name:
                                updates["mother_name"] = name
                        break

        if updates:
            client = get_supabase_client()
            client.table("user_family_profiles").update(updates).eq("user_id", str(user_id)).execute()
            log.info("profile_updated", user_id=str(user_id), fields=list(updates.keys()))
    except Exception:
        log.warning("profile_extract_failed", user_id=str(user_id), exc_info=True)
