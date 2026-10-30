from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.models import (
    DailyBriefing,
    PreferenceCandidate,
    PreferenceFeedback,
    PreferenceHistory,
    UserProfile,
)
from app.schemas.personal import ProfilePatch
from app.schemas.preferences import (
    PreferenceCandidateRead,
    PreferenceFeedbackCreate,
    PreferenceLearningRead,
)

PREFERENCE_FIELDS = (
    "working_hours",
    "study_sessions",
    "break_preferences",
    "focus_preferences",
    "planning_preferences",
    "task_presentation",
    "response_detail",
)
PROFILE_DEFAULTS = ProfilePatch().model_dump()


def get_learning_workspace(
    db: Session,
    owner_id: str = DEFAULT_OWNER_ID,
) -> PreferenceLearningRead:
    profile = db.get(UserProfile, owner_id)
    current_preferences = {
        field: getattr(profile, field) if profile is not None else PROFILE_DEFAULTS[field]
        for field in PREFERENCE_FIELDS
    }
    candidates = db.scalars(
        select(PreferenceCandidate)
        .where(PreferenceCandidate.owner_id == owner_id)
        .order_by(
            (PreferenceCandidate.status == "pending").desc(),
            PreferenceCandidate.created_at.desc(),
        )
        .limit(100)
    ).all()
    feedback = db.scalars(
        select(PreferenceFeedback)
        .where(PreferenceFeedback.owner_id == owner_id)
        .order_by(PreferenceFeedback.created_at.desc())
        .limit(50)
    ).all()
    briefing_dates = dict(
        db.execute(
            select(DailyBriefing.id, DailyBriefing.local_date).where(
                DailyBriefing.id.in_(
                    [item.briefing_id for item in feedback if item.briefing_id]
                )
            )
        ).all()
    ) if any(item.briefing_id for item in feedback) else {}
    history = db.scalars(
        select(PreferenceHistory)
        .where(PreferenceHistory.owner_id == owner_id)
        .order_by(PreferenceHistory.created_at.desc())
        .limit(100)
    ).all()
    return PreferenceLearningRead(
        current_preferences=current_preferences,
        feedback=[
            {
                "id": item.id,
                "briefing_id": item.briefing_id,
                "local_date": briefing_dates.get(item.briefing_id),
                "rating": item.rating,
                "comment": item.comment,
                "created_at": item.created_at,
            }
            for item in feedback
        ],
        candidates=[
            _candidate_read(candidate, current_preferences[candidate.preference_field])
            for candidate in candidates
        ],
        history=history,
    )


def record_feedback(
    db: Session,
    payload: PreferenceFeedbackCreate,
    owner_id: str = DEFAULT_OWNER_ID,
) -> PreferenceFeedback:
    briefing = db.scalar(
        select(DailyBriefing).where(
            DailyBriefing.owner_id == owner_id,
            DailyBriefing.local_date == payload.local_date,
        )
    )
    record = (
        db.scalar(
            select(PreferenceFeedback).where(
                PreferenceFeedback.owner_id == owner_id,
                PreferenceFeedback.briefing_id == briefing.id,
            )
        )
        if briefing
        else None
    )
    if record is None:
        record = PreferenceFeedback(
            owner_id=owner_id,
            briefing_id=briefing.id if briefing else None,
            rating=payload.rating,
            comment=payload.comment,
        )
        db.add(record)
    else:
        record.rating = payload.rating
        record.comment = payload.comment
    db.flush()

    if payload.preference_field is not None and payload.candidate_value is not None:
        candidate = db.scalar(
            select(PreferenceCandidate).where(
                PreferenceCandidate.owner_id == owner_id,
                PreferenceCandidate.feedback_id == record.id,
                PreferenceCandidate.preference_field == payload.preference_field,
            )
        )
        if candidate is None:
            candidate = PreferenceCandidate(
                owner_id=owner_id,
                feedback_id=record.id,
                preference_field=payload.preference_field,
                candidate_value=payload.candidate_value,
                status="pending",
                auto_applied=False,
            )
            db.add(candidate)
            db.flush()
        elif candidate.status == "pending":
            candidate.candidate_value = payload.candidate_value
        elif candidate.candidate_value != payload.candidate_value or payload.explicitly_requested:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This preference candidate has already been decided.",
            )
        if payload.explicitly_requested:
            if candidate.status == "pending":
                candidate.auto_applied = True
                _apply_candidate(db, candidate, owner_id)

    db.commit()
    db.refresh(record)
    return record


def update_candidate(
    db: Session,
    candidate_id: str,
    candidate_value: str,
    owner_id: str = DEFAULT_OWNER_ID,
) -> PreferenceCandidate:
    candidate = _get_candidate(db, candidate_id, owner_id)
    if candidate.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending preference candidates can be edited.",
        )
    candidate.candidate_value = candidate_value
    db.commit()
    db.refresh(candidate)
    return candidate


def accept_candidate(
    db: Session,
    candidate_id: str,
    owner_id: str = DEFAULT_OWNER_ID,
) -> PreferenceCandidate:
    candidate = _get_candidate(db, candidate_id, owner_id)
    if candidate.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending preference candidates can be accepted.",
        )
    _apply_candidate(db, candidate, owner_id)
    db.commit()
    db.refresh(candidate)
    return candidate


def reject_candidate(
    db: Session,
    candidate_id: str,
    owner_id: str = DEFAULT_OWNER_ID,
) -> PreferenceCandidate:
    candidate = _get_candidate(db, candidate_id, owner_id)
    if candidate.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending preference candidates can be rejected.",
        )
    candidate.status = "rejected"
    candidate.decided_at = datetime.now(UTC)
    db.commit()
    db.refresh(candidate)
    return candidate


def undo_preference(
    db: Session,
    history_id: str,
    owner_id: str = DEFAULT_OWNER_ID,
) -> PreferenceHistory:
    history = db.scalar(
        select(PreferenceHistory).where(
            PreferenceHistory.id == history_id,
            PreferenceHistory.owner_id == owner_id,
        )
    )
    if history is None:
        raise HTTPException(status_code=404, detail="Preference history entry not found.")
    if history.undone_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This preference change has already been undone.",
        )
    latest_history_id = db.scalar(
        select(PreferenceHistory.id)
        .where(
            PreferenceHistory.owner_id == owner_id,
            PreferenceHistory.preference_field == history.preference_field,
            PreferenceHistory.undone_at.is_(None),
        )
        .order_by(PreferenceHistory.created_at.desc(), PreferenceHistory.id.desc())
        .limit(1)
    )
    if latest_history_id != history.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Undo newer preference changes first.",
        )
    profile = _get_or_create_profile(db, owner_id)
    if getattr(profile, history.preference_field) != history.applied_value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This preference changed afterward. Review the current value before undoing.",
        )
    setattr(profile, history.preference_field, history.previous_value)
    history.undone_at = datetime.now(UTC)
    if history.candidate_id is not None:
        candidate = _get_candidate(db, history.candidate_id, owner_id)
        candidate.status = "undone"
    db.commit()
    db.refresh(history)
    return history


def candidate_read_for_api(
    db: Session,
    candidate: PreferenceCandidate,
    owner_id: str = DEFAULT_OWNER_ID,
) -> PreferenceCandidateRead:
    profile = db.get(UserProfile, owner_id)
    current_value = (
        getattr(profile, candidate.preference_field)
        if profile is not None
        else PROFILE_DEFAULTS[candidate.preference_field]
    )
    return _candidate_read(candidate, current_value)


def _apply_candidate(
    db: Session,
    candidate: PreferenceCandidate,
    owner_id: str,
) -> None:
    profile = _get_or_create_profile(db, owner_id)
    previous_value = getattr(profile, candidate.preference_field)
    if previous_value != candidate.candidate_value:
        setattr(profile, candidate.preference_field, candidate.candidate_value)
        db.add(
            PreferenceHistory(
                owner_id=owner_id,
                candidate_id=candidate.id,
                preference_field=candidate.preference_field,
                previous_value=previous_value,
                applied_value=candidate.candidate_value,
                source="candidate",
            )
        )
    candidate.status = "applied"
    candidate.decided_at = datetime.now(UTC)


def _get_or_create_profile(db: Session, owner_id: str) -> UserProfile:
    profile = db.get(UserProfile, owner_id)
    if profile is None:
        profile = UserProfile(id=owner_id, **PROFILE_DEFAULTS)
        db.add(profile)
        db.flush()
    return profile


def _get_candidate(
    db: Session,
    candidate_id: str,
    owner_id: str,
) -> PreferenceCandidate:
    candidate = db.scalar(
        select(PreferenceCandidate).where(
            PreferenceCandidate.id == candidate_id,
            PreferenceCandidate.owner_id == owner_id,
        )
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Preference candidate not found.")
    return candidate


def _candidate_read(
    candidate: PreferenceCandidate,
    current_value: str,
) -> PreferenceCandidateRead:
    return PreferenceCandidateRead(
        id=candidate.id,
        feedback_id=candidate.feedback_id,
        preference_field=candidate.preference_field,
        candidate_value=candidate.candidate_value,
        current_value=current_value,
        status=candidate.status,
        auto_applied=candidate.auto_applied,
        decided_at=candidate.decided_at,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )
