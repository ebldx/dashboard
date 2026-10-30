import argparse
from contextlib import closing
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import get_settings

FORMAT_VERSION = 1


def _sqlite_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("Backups currently support file-based SQLite databases only.")
    if url.database.startswith("file:"):
        raise ValueError("SQLite URI database paths are not supported for backups.")
    database_path = Path(url.database).expanduser()
    if database_path.is_symlink():
        raise ValueError(f"Refusing to back up symlinked database: {database_path}")
    return database_path.resolve()


def _reject_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise ValueError(f"Refusing to back up symlinked storage: {root}")
    if not root.exists():
        return
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in directories + filenames:
            path = current_path / name
            if path.is_symlink():
                raise ValueError(f"Refusing to back up symlinked storage entry: {path}")
            if any("\\" in part or part in {".", ".."} for part in path.relative_to(root).parts):
                raise ValueError(f"Refusing unsafe storage entry name: {path}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_private_file(archive: zipfile.ZipFile, path: Path, name: str) -> None:
    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    with path.open("rb") as source, archive.open(info, "w") as target:
        shutil.copyfileobj(source, target)


def create_backup(
    destination: Path,
    database_url: str,
    file_storage_dir: Path,
    *,
    now: datetime | None = None,
    keep: int = 14,
) -> Path:
    if keep < 1:
        raise ValueError("At least one backup must be retained.")
    database_path = _sqlite_path(database_url)
    raw_storage_path = file_storage_dir.expanduser()
    if raw_storage_path.is_symlink():
        raise ValueError(f"Refusing to back up symlinked storage: {raw_storage_path}")
    storage_path = raw_storage_path.resolve()
    destination = destination.expanduser().resolve()

    if not database_path.is_file():
        raise FileNotFoundError(f"SQLite database does not exist: {database_path}")
    if destination == storage_path or storage_path in destination.parents:
        raise ValueError("Backup destination must not be inside the file storage directory.")
    _reject_symlinks(database_path)
    _reject_symlinks(storage_path)
    if storage_path.exists() and not storage_path.is_dir():
        raise ValueError(f"File storage path is not a directory: {storage_path}")

    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        destination.chmod(0o700)
    except OSError:
        pass

    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    filename = f"daymark-backup-{timestamp.strftime('%Y%m%dT%H%M%S.%fZ')}.zip"
    archive_path = destination / filename
    if archive_path.exists():
        raise FileExistsError(f"Backup already exists: {archive_path}")
    temporary_archive = destination / f".{filename}.tmp"

    try:
        with tempfile.TemporaryDirectory(prefix="daymark-backup-") as temporary:
            stage = Path(temporary)
            staged_database = stage / "dashboard.db"
            staged_files = stage / "files"

            with closing(sqlite3.connect(database_path)) as source, closing(
                sqlite3.connect(staged_database)
            ) as target:
                source.backup(target)
                result = target.execute("PRAGMA integrity_check").fetchone()
                if result is None or result[0] != "ok":
                    raise RuntimeError("SQLite integrity check failed for the backup.")
                target.commit()

            if storage_path.exists():
                shutil.copytree(storage_path, staged_files, symlinks=True)
                _reject_symlinks(staged_files)
            else:
                staged_files.mkdir()

            entries = [
                (staged_database, "database/dashboard.db"),
                *(
                    (path, f"files/{path.relative_to(staged_files).as_posix()}")
                    for path in sorted(staged_files.rglob("*"))
                    if path.is_file()
                ),
            ]
            manifest = {
                "format_version": FORMAT_VERSION,
                "created_at": timestamp.isoformat(),
                "files": [
                    {
                        "path": name,
                        "size_bytes": path.stat().st_size,
                        "sha256": _sha256(path),
                    }
                    for path, name in entries
                ],
            }

            with zipfile.ZipFile(
                temporary_archive,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as archive:
                for path, name in entries:
                    _write_private_file(archive, path, name)
                manifest_info = zipfile.ZipInfo("manifest.json")
                manifest_info.compress_type = zipfile.ZIP_DEFLATED
                manifest_info.external_attr = (stat.S_IFREG | 0o600) << 16
                archive.writestr(
                    manifest_info,
                    json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"),
                )

        os.chmod(temporary_archive, 0o600)
        os.replace(temporary_archive, archive_path)
    finally:
        if temporary_archive.exists():
            temporary_archive.unlink()
    existing_backups = sorted(
        (
            path
            for path in destination.iterdir()
            if path.name.startswith("daymark-backup-")
            and path.suffix == ".zip"
            and path.is_file()
            and not path.is_symlink()
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    for old_backup in existing_backups[keep:]:
        old_backup.unlink()
    return archive_path


def verify_backup(archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "manifest.json" not in names:
            raise ValueError("Backup archive contains duplicate entries or no manifest.")
        if archive.testzip() is not None:
            raise ValueError("Backup archive failed its ZIP integrity check.")
        try:
            manifest = json.loads(archive.read("manifest.json"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Backup manifest is invalid.") from exc
        if not isinstance(manifest, dict):
            raise ValueError("Backup manifest is invalid.")
        if manifest.get("format_version") != FORMAT_VERSION:
            raise ValueError("Backup format version is not supported.")
        files = manifest.get("files")
        if not isinstance(files, list):
            raise ValueError("Backup manifest has no file list.")
        expected_names = {"manifest.json"}
        records: set[str] = set()
        for item in files:
            if not isinstance(item, dict):
                raise ValueError("Backup manifest contains an invalid file record.")
            name = item.get("path")
            if (
                not isinstance(name, str)
                or "\\" in name
                or name.startswith("/")
                or any(part in {"", ".", ".."} for part in name.split("/"))
                or name in records
                or (name != "database/dashboard.db" and not name.startswith("files/"))
            ):
                raise ValueError("Backup manifest contains an unsafe or duplicate path.")
            if (
                not isinstance(item.get("size_bytes"), int)
                or isinstance(item.get("size_bytes"), bool)
                or item["size_bytes"] < 0
                or not isinstance(item.get("sha256"), str)
                or len(item["sha256"]) != 64
                or any(character not in "0123456789abcdef" for character in item["sha256"])
            ):
                raise ValueError("Backup manifest contains invalid integrity metadata.")
            expected_names.add(name)
            records.add(name)
            digest = hashlib.sha256()
            size = 0
            try:
                with archive.open(name) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                        size += len(chunk)
            except KeyError as exc:
                raise ValueError(f"Backup is missing {name}.") from exc
            if size != item.get("size_bytes") or digest.hexdigest() != item.get("sha256"):
                raise ValueError(f"Backup integrity check failed for {name}.")
        if "database/dashboard.db" not in records or set(names) != expected_names:
            raise ValueError("Backup contents do not match the manifest.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or verify a private SQLite and uploaded-file backup archive."
    )
    parser.add_argument(
        "destination",
        nargs="?",
        type=Path,
        help="Directory for the timestamped backup archive.",
    )
    parser.add_argument("--verify", type=Path, help="Verify an existing backup archive.")
    parser.add_argument(
        "--keep",
        type=int,
        default=14,
        help="Number of newest matching backup archives to keep (default: 14).",
    )
    args = parser.parse_args()
    if bool(args.destination) == bool(args.verify):
        parser.error("Provide a destination directory or --verify, but not both.")
    try:
        if args.verify:
            verify_backup(args.verify)
            print(f"Backup verified: {args.verify}")
            return 0
        settings = get_settings()
        backup_path = create_backup(
            args.destination,
            settings.database_url,
            Path(settings.file_storage_dir),
            keep=args.keep,
        )
        print(backup_path)
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error, zipfile.BadZipFile) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
