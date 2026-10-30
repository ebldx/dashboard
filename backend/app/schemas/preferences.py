from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.personal import APIModel

PreferenceField = Literal[
    "working_hours",
    "study_sessions",
    "break_preferences",
    "focus_preferences",
    "planning_preferences",
    "task_presentation",
    "response_detail",
]


class PreferenceFeedbackCreate(APIModel):
    local_date: date
    rating: Literal[-1, 0, 1]
    comment: str = Field(default="", max_length=2000)
    preference_field: PreferenceField | None = None
    candidate_value: str | None = Field(default=None, min_length=1, max_length=2000)
    explicitly_requested: bool = False

    @model_validator(mode="after")
    def validate_candidate(self) -> "PreferenceFeedbackCreate":
        if (self.preference_field is None) != (self.candidate_value is None):
            raise ValueError(
                "preference_field and candidate_value must be provided together"
            )
        if self.explicitly_requested and self.preference_field is None:
            raise ValueError(
                "An explicit preference must include a field and candidate value"
            )
        return self


class PreferenceFeedbackRead(APIModel):
    id: str
    briefing_id: str | None
    local_date: date | None
    rating: Literal[-1, 0, 1]
    comment: str
    created_at: datetime


class PreferenceCandidateUpdate(APIModel):
    candidate_value: str = Field(min_length=1, max_length=2000)


class PreferenceCandidateRead(APIModel):
    id: str
    feedback_id: str | None
    preference_field: PreferenceField
    candidate_value: str
    current_value: str
    status: Literal["pending", "applied", "rejected", "undone"]
    auto_applied: bool
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PreferenceHistoryRead(APIModel):
    id: str
    candidate_id: str | None
    preference_field: PreferenceField
    previous_value: str
    applied_value: str
    source: Literal["candidate", "profile_edit"]
    undone_at: datetime | None
    created_at: datetime


class PreferenceLearningRead(APIModel):
    current_preferences: dict[str, str]
    feedback: list[PreferenceFeedbackRead]
    candidates: list[PreferenceCandidateRead]
    history: list[PreferenceHistoryRead]
