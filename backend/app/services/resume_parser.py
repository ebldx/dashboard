import re
import unicodedata
import zipfile
from collections.abc import Iterable
from io import BytesIO

from docx import Document
from pypdf import PdfReader

MAX_EXTRACTED_TEXT = 200_000
MAX_DOCX_UNCOMPRESSED_BYTES = 50_000_000

SECTION_HEADINGS = {
    "experience": "experience",
    "work experience": "experience",
    "employment": "experience",
    "employment history": "experience",
    "professional experience": "experience",
    "arbeidserfaring": "experience",
    "education": "education",
    "academic background": "education",
    "utdanning": "education",
    "skills": "skill",
    "technical skills": "skill",
    "technical tools": "skill",
    "programming languages": "skill",
    "competencies": "skill",
    "ferdigheter": "skill",
    "certifications": "certification",
    "certificates": "certification",
    "sertifiseringer": "certification",
    "languages": "language",
    "sprak": "language",
    "projects": "project",
    "prosjekter": "project",
    "selected projects": "project",
    "achievements": "achievement",
    "responsibilities": "responsibility",
    "interests": "interest",
    "professional interests": "interest",
}

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}(?!\w)")


class ResumeParseError(ValueError):
    pass


def _extract_pdf(data: bytes) -> list[str]:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ResumeParseError("Password-protected PDF files are not supported.")
        if len(reader.pages) > 100:
            raise ResumeParseError("PDF files must contain no more than 100 pages.")
        return [page.extract_text() or "" for page in reader.pages]
    except ResumeParseError:
        raise
    except Exception as exc:
        raise ResumeParseError("The PDF could not be read. Check that the file is valid and not password-protected.") from exc


def _extract_docx(data: bytes) -> list[str]:
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            if len(archive.infolist()) > 2000 or sum(
                item.file_size for item in archive.infolist()
            ) > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise ResumeParseError("The DOCX document contains too much expanded content.")
            if "[Content_Types].xml" not in archive.namelist() or "word/document.xml" not in archive.namelist():
                raise ResumeParseError("The DOCX document is missing required document content.")
        document = Document(BytesIO(data))
        return [paragraph.text for paragraph in document.paragraphs]
    except ResumeParseError:
        raise
    except Exception as exc:
        raise ResumeParseError("The DOCX file could not be read.") from exc


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lstrip("•*- \t")


def _heading_key(line: str) -> str:
    normalized = unicodedata.normalize("NFKD", line.casefold())
    ascii_line = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z ]", "", ascii_line).strip()


def extract_resume_facts(data: bytes, media_type: str) -> list[tuple[str, str]]:
    lines = _extract_pdf(data) if media_type == "application/pdf" else _extract_docx(data)
    normalized = [_clean_line(line) for line in lines]
    text = "\n".join(line for line in normalized if line)[:MAX_EXTRACTED_TEXT]
    facts: list[tuple[str, str]] = []

    email = EMAIL_PATTERN.search(text)
    if email:
        facts.append(("contact", f"Email: {email.group(0)}"))
    phone = PHONE_PATTERN.search(text)
    if phone and not re.fullmatch(
        r"(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}",
        phone.group(0),
    ):
        facts.append(("contact", f"Phone: {phone.group(0)}"))

    current_category = "other"
    section_values: list[str] = []
    seen: set[tuple[str, str]] = set()

    def append_section(category: str, values: Iterable[str]) -> None:
        for value in values:
            clean_value = _clean_line(value)
            if not clean_value or len(clean_value) > 1000:
                continue
            item = (category, clean_value)
            if item not in seen:
                seen.add(item)
                facts.append(item)

    for line in normalized:
        if not line:
            continue
        heading = _heading_key(line).rstrip(": ")
        category = SECTION_HEADINGS.get(heading)
        if category:
            append_section(current_category, section_values)
            current_category = category
            section_values = []
        else:
            section_values.append(line)
    append_section(current_category, section_values)

    if len(facts) > 500:
        return facts[:500]
    return facts
