from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.models import (
    AcademicGoal,
    CareerGoal,
    Project,
    ProjectMilestone,
    Task,
)
from app.db.session import get_db
from app.schemas.work import (
    MilestoneCreate,
    MilestonePatch,
    MilestoneRead,
    ProjectCreate,
    ProjectPatch,
    ProjectRead,
)

router = APIRouter(tags=["projects"])


def _project_query():
    return select(Project).options(
        selectinload(Project.career_goals),
        selectinload(Project.academic_goals),
        selectinload(Project.milestones),
        selectinload(Project.tasks),
    )


def _project_read(project: Project) -> ProjectRead:
    milestone_count = len(project.milestones)
    completed_milestones = sum(item.status == "completed" for item in project.milestones)
    task_count = len(project.tasks)
    completed_tasks = sum(item.status == "completed" for item in project.tasks)
    completed_count = completed_milestones + completed_tasks
    work_count = milestone_count + task_count
    progress = round(100 * completed_count / work_count) if work_count else 0
    return ProjectRead(
        id=project.id,
        title=project.title,
        description=project.description,
        purpose=project.purpose,
        category=project.category,
        status=project.status,
        importance=project.importance,
        start_date=project.start_date,
        target_date=project.target_date,
        estimated_effort_hours=project.estimated_effort_hours,
        actual_effort_hours=project.actual_effort_hours,
        notes=project.notes,
        acquired_skills=project.acquired_skills,
        career_goal_ids=[goal.id for goal in project.career_goals],
        academic_goal_ids=[goal.id for goal in project.academic_goals],
        career_goal_titles=[goal.title for goal in project.career_goals],
        academic_goal_titles=[goal.title for goal in project.academic_goals],
        milestone_count=milestone_count,
        completed_milestone_count=completed_milestones,
        task_count=task_count,
        completed_task_count=completed_tasks,
        progress_percent=progress,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _get_project(session: Session, project_id: str) -> Project:
    project = session.scalar(
        _project_query().where(
            Project.id == project_id,
            Project.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _resolve_goal_relationships(
    session: Session,
    career_goal_ids: list[str] | None,
    academic_goal_ids: list[str] | None,
) -> tuple[list[CareerGoal] | None, list[AcademicGoal] | None]:
    career_goals = None
    if career_goal_ids is not None:
        if len(set(career_goal_ids)) != len(career_goal_ids):
            raise HTTPException(status_code=422, detail="Career goal IDs must be unique")
        career_goals = list(
            session.scalars(
                select(CareerGoal).where(
                    CareerGoal.id.in_(career_goal_ids),
                    CareerGoal.owner_id == DEFAULT_OWNER_ID,
                )
            )
        ) if career_goal_ids else []
        if len(career_goals) != len(career_goal_ids):
            raise HTTPException(status_code=422, detail="One or more career goals were not found")

    academic_goals = None
    if academic_goal_ids is not None:
        if len(set(academic_goal_ids)) != len(academic_goal_ids):
            raise HTTPException(status_code=422, detail="Academic goal IDs must be unique")
        academic_goals = list(
            session.scalars(
                select(AcademicGoal).where(
                    AcademicGoal.id.in_(academic_goal_ids),
                    AcademicGoal.owner_id == DEFAULT_OWNER_ID,
                )
            )
        ) if academic_goal_ids else []
        if len(academic_goals) != len(academic_goal_ids):
            raise HTTPException(status_code=422, detail="One or more academic goals were not found")
    return career_goals, academic_goals


@router.get("", response_model=list[ProjectRead])
def list_projects(session: Session = Depends(get_db)) -> list[ProjectRead]:
    projects = session.scalars(
        _project_query()
        .where(Project.owner_id == DEFAULT_OWNER_ID)
        .order_by(Project.updated_at.desc())
    )
    return [_project_read(project) for project in projects]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    session: Session = Depends(get_db),
) -> ProjectRead:
    values = project.model_dump()
    career_goal_ids = values.pop("career_goal_ids")
    academic_goal_ids = values.pop("academic_goal_ids")
    career_goals, academic_goals = _resolve_goal_relationships(
        session, career_goal_ids, academic_goal_ids
    )
    record = Project(
        owner_id=DEFAULT_OWNER_ID,
        **values,
        career_goals=career_goals or [],
        academic_goals=academic_goals or [],
    )
    session.add(record)
    session.commit()
    return _project_read(_get_project(session, record.id))


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, session: Session = Depends(get_db)) -> ProjectRead:
    return _project_read(_get_project(session, project_id))


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str,
    changes: ProjectPatch,
    session: Session = Depends(get_db),
) -> ProjectRead:
    project = _get_project(session, project_id)
    values = changes.model_dump(exclude_unset=True)
    career_goal_ids = values.pop("career_goal_ids", None)
    academic_goal_ids = values.pop("academic_goal_ids", None)
    career_goals, academic_goals = _resolve_goal_relationships(
        session, career_goal_ids, academic_goal_ids
    )
    start_date = values.get("start_date", project.start_date)
    target_date = values.get("target_date", project.target_date)
    if start_date and target_date and target_date < start_date:
        raise HTTPException(status_code=422, detail="target_date cannot be before start_date")
    for field, value in values.items():
        if value is None and field not in {
            "start_date",
            "target_date",
            "estimated_effort_hours",
            "actual_effort_hours",
        }:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
        setattr(project, field, value)
    if career_goals is not None:
        project.career_goals = career_goals
    if academic_goals is not None:
        project.academic_goals = academic_goals
    session.commit()
    return _project_read(_get_project(session, project_id))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, session: Session = Depends(get_db)) -> Response:
    project = _get_project(session, project_id)
    for task in project.tasks:
        task.project_id = None
        task.milestone_id = None
    session.delete(project)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/milestones", response_model=list[MilestoneRead])
def list_milestones(
    project_id: str,
    session: Session = Depends(get_db),
) -> list[MilestoneRead]:
    _get_project(session, project_id)
    milestones = session.scalars(
        select(ProjectMilestone)
        .options(selectinload(ProjectMilestone.tasks))
        .where(
            ProjectMilestone.project_id == project_id,
            ProjectMilestone.owner_id == DEFAULT_OWNER_ID,
        )
        .order_by(ProjectMilestone.target_date, ProjectMilestone.created_at)
    )
    return [
        MilestoneRead(
            id=item.id,
            project_id=item.project_id,
            title=item.title,
            description=item.description,
            target_date=item.target_date,
            status=item.status,
            completed_at=item.completed_at,
            task_count=len(item.tasks),
            completed_task_count=sum(task.status == "completed" for task in item.tasks),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in milestones
    ]


@router.post(
    "/{project_id}/milestones",
    response_model=MilestoneRead,
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    project_id: str,
    milestone: MilestoneCreate,
    session: Session = Depends(get_db),
) -> MilestoneRead:
    _get_project(session, project_id)
    completed_at = datetime.now(UTC) if milestone.status == "completed" else None
    record = ProjectMilestone(
        owner_id=DEFAULT_OWNER_ID,
        project_id=project_id,
        completed_at=completed_at,
        **milestone.model_dump(),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return MilestoneRead(
        id=record.id,
        project_id=record.project_id,
        title=record.title,
        description=record.description,
        target_date=record.target_date,
        status=record.status,
        completed_at=record.completed_at,
        task_count=0,
        completed_task_count=0,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.patch("/{project_id}/milestones/{milestone_id}", response_model=MilestoneRead)
def update_milestone(
    project_id: str,
    milestone_id: str,
    changes: MilestonePatch,
    session: Session = Depends(get_db),
) -> MilestoneRead:
    _get_project(session, project_id)
    milestone = session.scalar(
        select(ProjectMilestone)
        .options(selectinload(ProjectMilestone.tasks))
        .where(
            ProjectMilestone.id == milestone_id,
            ProjectMilestone.project_id == project_id,
            ProjectMilestone.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if milestone is None:
        raise HTTPException(status_code=404, detail="Project milestone not found")
    values = changes.model_dump(exclude_unset=True)
    for field, value in values.items():
        if value is None and field != "target_date":
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
        setattr(milestone, field, value)
    if "status" in values:
        milestone.completed_at = (
            datetime.now(UTC) if milestone.status == "completed" else None
        )
    session.commit()
    session.refresh(milestone)
    return MilestoneRead(
        id=milestone.id,
        project_id=milestone.project_id,
        title=milestone.title,
        description=milestone.description,
        target_date=milestone.target_date,
        status=milestone.status,
        completed_at=milestone.completed_at,
        task_count=len(milestone.tasks),
        completed_task_count=sum(task.status == "completed" for task in milestone.tasks),
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
    )


@router.delete(
    "/{project_id}/milestones/{milestone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_milestone(
    project_id: str,
    milestone_id: str,
    session: Session = Depends(get_db),
) -> Response:
    _get_project(session, project_id)
    milestone = session.scalar(
        select(ProjectMilestone).where(
            ProjectMilestone.id == milestone_id,
            ProjectMilestone.project_id == project_id,
            ProjectMilestone.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if milestone is None:
        raise HTTPException(status_code=404, detail="Project milestone not found")
    for task in milestone.tasks:
        task.milestone_id = None
    session.delete(milestone)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
