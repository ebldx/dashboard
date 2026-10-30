import hashlib
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.ownership import DEFAULT_OWNER_ID
from app.db.models import ResumeDocument, ResumeFact
from app.db.session import get_db
from app.schemas.personal import (
    ResumeDocumentRead,
    ResumeDocumentSummary,
    ResumeFactPatch,
    ResumeFactRead,
)
from app.services.resume_parser import ResumeParseError, extract_resume_facts

router = APIRouter(tags=["resume"])

PDF_MEDIA_TYPE = "application/pdf"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED_EXTENSIONS = {".pdf": PDF_MEDIA_TYPE, ".docx": DOCX_MEDIA_TYPE}
CHUNK_SIZE = 64 * 1024
FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._ -]")


def _safe_filename(filename: str) -> str:
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1]
    sanitized = FILENAME_PATTERN.sub("_", basename).strip(" .")
    return sanitized[:200] or "resume"


def _stored_path(storage_key: str) -> Path:
    root = Path(get_settings().file_storage_dir).resolve()
    path = (root / storage_key).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(status_code=500, detail="Invalid stored document reference")
    return path


def _validate_document(data: bytes, extension: str) -> str:
    expected_type = ALLOWED_EXTENSIONS[extension]
    if extension == ".pdf" and not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="The uploaded file is not a valid PDF.")
    if extension == ".docx":
        if not data.startswith(b"PK"):
            raise HTTPException(status_code=422, detail="The uploaded file is not a valid DOCX document.")
    return expected_type


async def _read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(CHUNK_SIZE):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Resume files must be no larger than {max_bytes // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    return b"".join(chunks)


@router.post(
    "/upload",
    response_model=ResumeDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
) -> ResumeDocument:
    original_filename = _safe_filename(file.filename or "")
    extension = Path(original_filename).suffix.casefold()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only PDF and DOCX resume files are supported.")

    settings = get_settings()
    max_bytes = settings.max_resume_size_mb * 1024 * 1024
    contents = await _read_limited(file, max_bytes)
    media_type = _validate_document(contents, extension)
    try:
        extracted = extract_resume_facts(contents, media_type)
    except ResumeParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    storage_key = f"{uuid4().hex}{extension}"
    storage_path = _stored_path(storage_key)
    storage_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        storage_path.write_bytes(contents)
        if os.name == "posix":
            os.chmod(storage_path.parent, 0o700)
            os.chmod(storage_path, 0o600)

        current_version = session.scalar(
            select(func.max(ResumeDocument.version)).where(
                ResumeDocument.owner_id == DEFAULT_OWNER_ID
            )
        ) or 0
        document = ResumeDocument(
            owner_id=DEFAULT_OWNER_ID,
            original_filename=original_filename,
            storage_key=storage_key,
            media_type=media_type,
            file_size=len(contents),
            sha256=hashlib.sha256(contents).hexdigest(),
            version=current_version + 1,
            extracted_at=datetime.now(UTC),
            extraction_status="pending_review",
            facts=[
                ResumeFact(category=category, value=value, verified=False)
                for category, value in extracted
            ],
        )
        session.add(document)
        session.commit()
        session.refresh(document)
    except IntegrityError as exc:
        session.rollback()
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=409,
            detail="Another resume was uploaded concurrently. Please retry.",
        ) from exc
    except Exception:
        session.rollback()
        storage_path.unlink(missing_ok=True)
        raise
    return document


@router.get("", response_model=list[ResumeDocumentSummary])
def list_resumes(session: Session = Depends(get_db)) -> list[ResumeDocumentSummary]:
    documents = session.scalars(
        select(ResumeDocument)
        .options(selectinload(ResumeDocument.facts))
        .where(ResumeDocument.owner_id == DEFAULT_OWNER_ID)
        .order_by(ResumeDocument.uploaded_at.desc())
    )
    return [
        ResumeDocumentSummary(
            id=document.id,
            original_filename=document.original_filename,
            media_type=document.media_type,
            file_size=document.file_size,
            version=document.version,
            uploaded_at=document.uploaded_at,
            extracted_at=document.extracted_at,
            extraction_status=document.extraction_status,
            fact_count=len(document.facts),
            verified_fact_count=sum(fact.verified for fact in document.facts),
        )
        for document in documents
    ]


@router.get("/{document_id}", response_model=ResumeDocumentRead)
def get_resume(
    document_id: str,
    session: Session = Depends(get_db),
) -> ResumeDocument:
    document = session.scalar(
        select(ResumeDocument)
        .options(selectinload(ResumeDocument.facts))
        .where(
            ResumeDocument.id == document_id,
            ResumeDocument.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Resume document not found")
    return document


@router.get("/{document_id}/download")
def download_resume(
    document_id: str,
    session: Session = Depends(get_db),
) -> FileResponse:
    document = session.scalar(
        select(ResumeDocument).where(
            ResumeDocument.id == document_id,
            ResumeDocument.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Resume document not found")
    path = _stored_path(document.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored resume file is missing")
    return FileResponse(
        path,
        media_type=document.media_type,
        filename=document.original_filename,
        content_disposition_type="attachment",
    )


@router.post("/{document_id}/extract", response_model=ResumeDocumentRead)
def reextract_resume(
    document_id: str,
    session: Session = Depends(get_db),
) -> ResumeDocument:
    document = session.scalar(
        select(ResumeDocument)
        .options(selectinload(ResumeDocument.facts))
        .where(
            ResumeDocument.id == document_id,
            ResumeDocument.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Resume document not found")
    path = _stored_path(document.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored resume file is missing")
    try:
        extracted = extract_resume_facts(path.read_bytes(), document.media_type)
    except ResumeParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    document.facts.clear()
    document.facts.extend(
        ResumeFact(category=category, value=value, verified=False)
        for category, value in extracted
    )
    document.extracted_at = datetime.now(UTC)
    document.extraction_status = "pending_review"
    session.commit()
    session.refresh(document)
    return document


@router.patch("/{document_id}/facts/{fact_id}", response_model=ResumeFactRead)
def update_resume_fact(
    document_id: str,
    fact_id: str,
    changes: ResumeFactPatch,
    session: Session = Depends(get_db),
) -> ResumeFact:
    fact = session.scalar(
        select(ResumeFact)
        .join(ResumeDocument)
        .where(
            ResumeFact.id == fact_id,
            ResumeFact.document_id == document_id,
            ResumeDocument.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if fact is None:
        raise HTTPException(status_code=404, detail="Resume fact not found")
    for field, value in changes.model_dump(exclude_unset=True).items():
        if value is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
        setattr(fact, field, value)
    session.flush()
    unreviewed_facts = session.scalar(
        select(func.count(ResumeFact.id)).where(
            ResumeFact.document_id == document_id,
            ResumeFact.verified.is_(False),
        )
    )
    document = session.scalar(
        select(ResumeDocument).where(
            ResumeDocument.id == document_id,
            ResumeDocument.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if document is not None:
        document.extraction_status = "reviewed" if unreviewed_facts == 0 else "pending_review"
    session.commit()
    session.refresh(fact)
    return fact


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    document_id: str,
    session: Session = Depends(get_db),
) -> Response:
    document = session.scalar(
        select(ResumeDocument).where(
            ResumeDocument.id == document_id,
            ResumeDocument.owner_id == DEFAULT_OWNER_ID,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Resume document not found")
    storage_path = _stored_path(document.storage_key)
    session.delete(document)
    session.commit()
    storage_path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
