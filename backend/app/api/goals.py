from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.models import AcademicGoal, CareerGoal
from app.db.session import get_db
from app.schemas.personal import (
    AcademicGoalCreate,
    AcademicGoalPatch,
    AcademicGoalRead,
    CareerGoalCreate,
    CareerGoalPatch,
    CareerGoalRead,
)

router = APIRouter(tags=["goals"])


def _apply_changes(record: object, changes: dict[str, object], nullable: set[str]) -> None:
    for field, value in changes.items():
        if value is None and field not in nullable:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
        setattr(record, field, value)


@router.get("/career", response_model=list[CareerGoalRead])
def list_career_goals(session: Session = Depends(get_db)) -> list[CareerGoal]:
    statement = (
        select(CareerGoal)
        .where(CareerGoal.owner_id == DEFAULT_OWNER_ID)
        .order_by(CareerGoal.created_at.desc())
    )
    return list(session.scalars(statement))


@router.post(
    "/career",
    response_model=CareerGoalRead,
    status_code=status.HTTP_201_CREATED,
)
def create_career_goal(
    goal: CareerGoalCreate,
    session: Session = Depends(get_db),
) -> CareerGoal:
    record = CareerGoal(owner_id=DEFAULT_OWNER_ID, **goal.model_dump())
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@router.get("/career/{goal_id}", response_model=CareerGoalRead)
def get_career_goal(goal_id: str, session: Session = Depends(get_db)) -> CareerGoal:
    record = session.scalar(
        select(CareerGoal).where(
            CareerGoal.id == goal_id,
            CareerGoal.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Career goal not found")
    return record


@router.patch("/career/{goal_id}", response_model=CareerGoalRead)
def update_career_goal(
    goal_id: str,
    changes: CareerGoalPatch,
    session: Session = Depends(get_db),
) -> CareerGoal:
    record = session.scalar(
        select(CareerGoal).where(
            CareerGoal.id == goal_id,
            CareerGoal.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Career goal not found")
    _apply_changes(record, changes.model_dump(exclude_unset=True), set())
    session.commit()
    session.refresh(record)
    return record


@router.delete("/career/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_career_goal(goal_id: str, session: Session = Depends(get_db)) -> Response:
    record = session.scalar(
        select(CareerGoal).where(
            CareerGoal.id == goal_id,
            CareerGoal.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Career goal not found")
    session.delete(record)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/academic", response_model=list[AcademicGoalRead])
def list_academic_goals(session: Session = Depends(get_db)) -> list[AcademicGoal]:
    statement = (
        select(AcademicGoal)
        .where(AcademicGoal.owner_id == DEFAULT_OWNER_ID)
        .order_by(AcademicGoal.created_at.desc())
    )
    return list(session.scalars(statement))


@router.post(
    "/academic",
    response_model=AcademicGoalRead,
    status_code=status.HTTP_201_CREATED,
)
def create_academic_goal(
    goal: AcademicGoalCreate,
    session: Session = Depends(get_db),
) -> AcademicGoal:
    record = AcademicGoal(owner_id=DEFAULT_OWNER_ID, **goal.model_dump())
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@router.get("/academic/{goal_id}", response_model=AcademicGoalRead)
def get_academic_goal(goal_id: str, session: Session = Depends(get_db)) -> AcademicGoal:
    record = session.scalar(
        select(AcademicGoal).where(
            AcademicGoal.id == goal_id,
            AcademicGoal.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Academic goal not found")
    return record


@router.patch("/academic/{goal_id}", response_model=AcademicGoalRead)
def update_academic_goal(
    goal_id: str,
    changes: AcademicGoalPatch,
    session: Session = Depends(get_db),
) -> AcademicGoal:
    record = session.scalar(
        select(AcademicGoal).where(
            AcademicGoal.id == goal_id,
            AcademicGoal.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Academic goal not found")
    _apply_changes(record, changes.model_dump(exclude_unset=True), {"target_date"})
    session.commit()
    session.refresh(record)
    return record


@router.delete("/academic/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_academic_goal(goal_id: str, session: Session = Depends(get_db)) -> Response:
    record = session.scalar(
        select(AcademicGoal).where(
            AcademicGoal.id == goal_id,
            AcademicGoal.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Academic goal not found")
    session.delete(record)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
