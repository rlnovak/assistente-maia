from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.db.models import FamilyProfile, FamilyProfileUpdate, UserProfile
from app.services.profile_service import get_or_create_profile, update_profile

router = APIRouter()


@router.get("/profile", response_model=FamilyProfile)
def get_profile(
    current_user: UserProfile = Depends(get_current_user),
) -> FamilyProfile:
    return get_or_create_profile(current_user.id)


@router.put("/profile", response_model=FamilyProfile)
def put_profile(
    data: FamilyProfileUpdate,
    current_user: UserProfile = Depends(get_current_user),
) -> FamilyProfile:
    return update_profile(current_user.id, data)
