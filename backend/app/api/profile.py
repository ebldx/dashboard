from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.models import UserProfile
from app.db.session import get_db
from app.schemas.personal import ProfilePatch, ProfileRead
from app.services.preferences import PREFERENCE_FIELDS
from app.db.models import PreferenceHistory

router = APIRouter(tags=["profile"])

PROFILE_ID = DEFAULT_OWNER_ID
PROFILE_DEFAULTS = ProfilePatch().model_dump()


@router.get("", response_model=ProfileRead)
def get_profile(session: Session = Depends(get_db)) -> ProfileRead:
    profile = session.get(UserProfile, PROFILE_ID)
    if profile is not None:
        return ProfileRead.model_validate(profile)
    return ProfileRead(id=PROFILE_ID, **PROFILE_DEFAULTS)


@router.patch("", response_model=ProfileRead)
def update_profile(
    changes: ProfilePatch,
    session: Session = Depends(get_db),
) -> ProfileRead:
    profile = session.get(UserProfile, PROFILE_ID)
    if profile is None:
        profile = UserProfile(id=PROFILE_ID, **PROFILE_DEFAULTS)
        session.add(profile)

    updates = changes.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in PREFERENCE_FIELDS:
            previous_value = getattr(profile, field)
            if previous_value != value:
                session.add(
                    PreferenceHistory(
                        owner_id=PROFILE_ID,
                        candidate_id=None,
                        preference_field=field,
                        previous_value=previous_value,
                        applied_value=value,
                        source="profile_edit",
                    )
                )
        setattr(profile, field, value)

    session.commit()
    session.refresh(profile)
    return ProfileRead.model_validate(profile)
