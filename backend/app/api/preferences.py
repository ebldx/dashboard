from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.session import get_db
from app.schemas.preferences import (
    PreferenceCandidateRead,
    PreferenceCandidateUpdate,
    PreferenceFeedbackCreate,
    PreferenceFeedbackRead,
    PreferenceHistoryRead,
    PreferenceLearningRead,
)
from app.services.preferences import (
    accept_candidate,
    candidate_read_for_api,
    get_learning_workspace,
    record_feedback,
    reject_candidate,
    undo_preference,
    update_candidate,
)

router = APIRouter(tags=["preferences"])


@router.get("/learning", response_model=PreferenceLearningRead)
def get_preferences_learning(
    session: Session = Depends(get_db),
) -> PreferenceLearningRead:
    return get_learning_workspace(session, DEFAULT_OWNER_ID)


@router.post("/feedback", response_model=PreferenceFeedbackRead)
def submit_preference_feedback(
    payload: PreferenceFeedbackCreate,
    session: Session = Depends(get_db),
) -> PreferenceFeedbackRead:
    feedback = record_feedback(session, payload, DEFAULT_OWNER_ID)
    return PreferenceFeedbackRead(
        id=feedback.id,
        briefing_id=feedback.briefing_id,
        local_date=payload.local_date if feedback.briefing_id else None,
        rating=feedback.rating,
        comment=feedback.comment,
        created_at=feedback.created_at,
    )


@router.patch("/candidates/{candidate_id}", response_model=PreferenceCandidateRead)
def edit_candidate(
    candidate_id: str,
    changes: PreferenceCandidateUpdate,
    session: Session = Depends(get_db),
) -> PreferenceCandidateRead:
    candidate = update_candidate(
        session,
        candidate_id,
        changes.candidate_value,
        DEFAULT_OWNER_ID,
    )
    return candidate_read_for_api(session, candidate, DEFAULT_OWNER_ID)


@router.post("/candidates/{candidate_id}/accept", response_model=PreferenceCandidateRead)
def accept_preference_candidate(
    candidate_id: str,
    session: Session = Depends(get_db),
) -> PreferenceCandidateRead:
    candidate = accept_candidate(session, candidate_id, DEFAULT_OWNER_ID)
    return candidate_read_for_api(session, candidate, DEFAULT_OWNER_ID)


@router.post("/candidates/{candidate_id}/reject", response_model=PreferenceCandidateRead)
def reject_preference_candidate(
    candidate_id: str,
    session: Session = Depends(get_db),
) -> PreferenceCandidateRead:
    candidate = reject_candidate(session, candidate_id, DEFAULT_OWNER_ID)
    return candidate_read_for_api(session, candidate, DEFAULT_OWNER_ID)


@router.post("/history/{history_id}/undo", response_model=PreferenceHistoryRead)
def undo_preference_history(
    history_id: str,
    session: Session = Depends(get_db),
) -> PreferenceHistoryRead:
    return undo_preference(session, history_id, DEFAULT_OWNER_ID)
