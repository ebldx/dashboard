from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.models import (
    AcademicGoal,
    CareerGoal,
    Project,
    ProjectMilestone,
    Task,
)
from app.db.session import get_db
from app.schemas.work import TaskCreate, TaskPatch, TaskRead

router = APIRouter(tags=["tasks"])


def _task_query():
    return select(Task).options(
        joinedload(Task.project),
        joinedload(Task.milestone),
        joinedload(Task.career_goal),
        joinedload(Task.academic_goal),
    )


def _task_read(task: Task) -> TaskRead:
    return TaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        deadline=task.deadline,
        estimated_duration_minutes=task.estimated_duration_minutes,
        actual_duration_minutes=task.actual_duration_minutes,
        category=task.category,
        source="user",
        project_id=task.project_id,
        project_title=task.project.title if task.project else None,
        milestone_id=task.milestone_id,
        milestone_title=task.milestone.title if task.milestone else None,
        career_goal_id=task.career_goal_id,
        career_goal_title=task.career_goal.title if task.career_goal else None,
        academic_goal_id=task.academic_goal_id,
        academic_goal_title=task.academic_goal.title if task.academic_goal else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
    )


def _validate_relationships(
    session: Session,
    project_id: str | None,
    milestone_id: str | None,
    career_goal_id: str | None,
    academic_goal_id: str | None,
) -> None:
    if project_id is not None:
        project_exists = session.scalar(
            select(Project.id).where(
                Project.id == project_id,
                Project.owner_id == DEFAULT_OWNER_ID,
            )
        )
        if project_exists is None:
            raise HTTPException(status_code=422, detail="Project not found")
    if milestone_id is not None:
        milestone = session.scalar(
            select(ProjectMilestone).where(
                ProjectMilestone.id == milestone_id,
                ProjectMilestone.owner_id == DEFAULT_OWNER_ID,
            )
        )
        if milestone is None:
            raise HTTPException(status_code=422, detail="Project milestone not found")
        if project_id is None or milestone.project_id != project_id:
            raise HTTPException(
                status_code=422,
                detail="The milestone must belong to the selected project",
            )
    if career_goal_id is not None:
        goal_exists = session.scalar(
            select(CareerGoal.id).where(
                CareerGoal.id == career_goal_id,
                CareerGoal.owner_id == DEFAULT_OWNER_ID,
            )
        )
        if goal_exists is None:
            raise HTTPException(status_code=422, detail="Career goal not found")
    if academic_goal_id is not None:
        goal_exists = session.scalar(
            select(AcademicGoal.id).where(
                AcademicGoal.id == academic_goal_id,
                AcademicGoal.owner_id == DEFAULT_OWNER_ID,
            )
        )
        if goal_exists is None:
            raise HTTPException(status_code=422, detail="Academic goal not found")


def _get_task(session: Session, task_id: str) -> Task:
    task = session.scalar(
        _task_query().where(
            Task.id == task_id,
            Task.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("", response_model=list[TaskRead])
def list_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    category: str | None = None,
    project_id: str | None = None,
    deadline_from: date | None = None,
    deadline_to: date | None = None,
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> list[TaskRead]:
    statement = _task_query().where(Task.owner_id == DEFAULT_OWNER_ID)
    if status_filter is not None:
        statement = statement.where(Task.status == status_filter)
    if priority is not None:
        statement = statement.where(Task.priority == priority)
    if category is not None:
        statement = statement.where(Task.category == category)
    if project_id is not None:
        statement = statement.where(Task.project_id == project_id)
    if deadline_from is not None:
        statement = statement.where(Task.deadline >= deadline_from)
    if deadline_to is not None:
        statement = statement.where(Task.deadline <= deadline_to)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            Task.title.ilike(pattern) | Task.description.ilike(pattern)
        )
    tasks = session.scalars(
        statement.order_by(
            Task.deadline.is_(None),
            Task.deadline,
            Task.created_at.desc(),
        ).limit(limit).offset(offset)
    ).unique()
    return [_task_read(task) for task in tasks]


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, session: Session = Depends(get_db)) -> TaskRead:
    values = task.model_dump()
    _validate_relationships(
        session,
        values["project_id"],
        values["milestone_id"],
        values["career_goal_id"],
        values["academic_goal_id"],
    )
    completed_at = datetime.now(UTC) if values["status"] == "completed" else None
    record = Task(
        owner_id=DEFAULT_OWNER_ID,
        source="user",
        completed_at=completed_at,
        **values,
    )
    session.add(record)
    session.commit()
    return _task_read(_get_task(session, record.id))


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: str, session: Session = Depends(get_db)) -> TaskRead:
    return _task_read(_get_task(session, task_id))


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: str,
    changes: TaskPatch,
    session: Session = Depends(get_db),
) -> TaskRead:
    task = _get_task(session, task_id)
    values = changes.model_dump(exclude_unset=True)

    project_id = values.get("project_id", task.project_id)
    milestone_id = values.get("milestone_id", task.milestone_id)
    career_goal_id = values.get("career_goal_id", task.career_goal_id)
    academic_goal_id = values.get("academic_goal_id", task.academic_goal_id)
    _validate_relationships(
        session,
        project_id,
        milestone_id,
        career_goal_id,
        academic_goal_id,
    )

    for field, value in values.items():
        if value is None and field not in {
            "deadline",
            "estimated_duration_minutes",
            "actual_duration_minutes",
            "project_id",
            "milestone_id",
            "career_goal_id",
            "academic_goal_id",
        }:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
        setattr(task, field, value)

    if "status" in values:
        if task.status == "completed":
            task.completed_at = task.completed_at or datetime.now(UTC)
        else:
            task.completed_at = None
    session.commit()
    return _task_read(_get_task(session, task_id))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, session: Session = Depends(get_db)) -> Response:
    task = _get_task(session, task_id)
    session.delete(task)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
