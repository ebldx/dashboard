from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.models import PersonalPrinciple
from app.db.session import get_db
from app.schemas.personal import PrincipleCreate, PrinciplePatch, PrincipleRead

router = APIRouter(tags=["principles"])


@router.get("", response_model=list[PrincipleRead])
def list_principles(session: Session = Depends(get_db)) -> list[PersonalPrinciple]:
    return list(
        session.scalars(
            select(PersonalPrinciple)
            .where(PersonalPrinciple.owner_id == DEFAULT_OWNER_ID)
            .order_by(
                PersonalPrinciple.active.desc(),
                PersonalPrinciple.importance.desc(),
                PersonalPrinciple.created_at.desc(),
            )
        )
    )


@router.post("", response_model=PrincipleRead, status_code=status.HTTP_201_CREATED)
def create_principle(
    principle: PrincipleCreate,
    session: Session = Depends(get_db),
) -> PersonalPrinciple:
    record = PersonalPrinciple(owner_id=DEFAULT_OWNER_ID, **principle.model_dump())
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@router.patch("/{principle_id}", response_model=PrincipleRead)
def update_principle(
    principle_id: str,
    changes: PrinciplePatch,
    session: Session = Depends(get_db),
) -> PersonalPrinciple:
    record = session.scalar(
        select(PersonalPrinciple).where(
            PersonalPrinciple.id == principle_id,
            PersonalPrinciple.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Personal principle not found")
    for field, value in changes.model_dump(exclude_unset=True).items():
        if value is None and field != "reminder":
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
        setattr(record, field, value)
    session.commit()
    session.refresh(record)
    return record


@router.delete("/{principle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_principle(
    principle_id: str,
    session: Session = Depends(get_db),
) -> Response:
    record = session.scalar(
        select(PersonalPrinciple).where(
            PersonalPrinciple.id == principle_id,
            PersonalPrinciple.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Personal principle not found")
    session.delete(record)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
