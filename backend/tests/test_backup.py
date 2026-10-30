import hashlib
import json
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.backup import create_backup, verify_backup


def test_backup_contains_consistent_database_files_and_manifest(tmp_path: Path) -> None:
    database = tmp_path / "dashboard.db"
    storage = tmp_path / "files"
    storage.mkdir()
    (storage / "resume.bin").write_bytes(b"private resume content")
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample VALUES ('persisted')")

    output = create_backup(
        tmp_path / "backups",
        f"sqlite:///{database.as_posix()}",
        storage,
        now=datetime(2026, 10, 30, tzinfo=UTC),
    )

    assert output.name == "daymark-backup-20261030T000000.000000Z.zip"
    with zipfile.ZipFile(output) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert archive.read("files/resume.bin") == b"private resume content"
        with sqlite3.connect(":memory:") as restored:
            restored.deserialize(archive.read("database/dashboard.db"))
            assert restored.execute("SELECT value FROM sample").fetchone() == ("persisted",)
        database_record = next(
            item for item in manifest["files"] if item["path"] == "database/dashboard.db"
        )
        assert database_record["sha256"] == hashlib.sha256(
            archive.read("database/dashboard.db")
        ).hexdigest()
        verify_backup(output)


@pytest.mark.parametrize(
    ("database_url", "error"),
    [
        ("postgresql://localhost/dashboard", "SQLite"),
        ("sqlite:///:memory:", "SQLite"),
    ],
)
def test_backup_rejects_unsupported_database_urls(
    tmp_path: Path,
    database_url: str,
    error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        create_backup(tmp_path / "backups", database_url, tmp_path / "files")


def test_backup_rejects_destination_inside_uploaded_file_storage(tmp_path: Path) -> None:
    database = tmp_path / "dashboard.db"
    with sqlite3.connect(database):
        pass
    storage = tmp_path / "files"
    storage.mkdir()

    with pytest.raises(ValueError, match="inside the file storage"):
        create_backup(storage / "backups", f"sqlite:///{database.as_posix()}", storage)


def test_backup_retention_keeps_newest_archives_and_detects_tampering(
    tmp_path: Path,
) -> None:
    database = tmp_path / "dashboard.db"
    with sqlite3.connect(database):
        pass
    backups = tmp_path / "backups"
    for day in (1, 2, 3):
        create_backup(
            backups,
            f"sqlite:///{database.as_posix()}",
            tmp_path / "files",
            now=datetime(2026, 10, day, tzinfo=UTC),
            keep=2,
        )

    archives = sorted(backups.glob("daymark-backup-*.zip"))
    assert len(archives) == 2
    assert "20261002" in archives[0].name
    verify_backup(archives[-1])

    with zipfile.ZipFile(archives[-1], "a") as archive:
        archive.writestr("files/tampered.bin", b"unexpected")
    with pytest.raises(ValueError, match="do not match the manifest"):
        verify_backup(archives[-1])
