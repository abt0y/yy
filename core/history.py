from __future__ import annotations

import secrets
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile


@dataclass(slots=True)
class FileRecord:
    id: str
    filename: str
    path: Path
    bytes: int
    purpose: str


class FileStore:
    def __init__(self, upload_dir: Path) -> None:
        self._upload_dir = upload_dir
        self._records: dict[str, FileRecord] = {}

    def list_files(self) -> list[FileRecord]:
        return list(self._records.values())

    def get_paths(self, file_ids: list[str]) -> list[Path]:
        paths: list[Path] = []
        for file_id in file_ids:
            record = self._records.get(file_id)
            if record is not None:
                paths.append(record.path)
        return paths

    async def save(self, upload: UploadFile, purpose: str) -> FileRecord:
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        file_id = f"file-{secrets.token_hex(12)}"
        safe_name = Path(upload.filename or "upload.bin").name
        path = self._upload_dir / f"{file_id}-{safe_name}"
        data = await upload.read()
        path.write_bytes(data)
        record = FileRecord(id=file_id, filename=safe_name, path=path, bytes=len(data), purpose=purpose)
        self._records[file_id] = record
        return record

    def delete(self, file_id: str) -> bool:
        record = self._records.pop(file_id, None)
        if record is None:
            return False
        if record.path.exists():
            record.path.unlink()
        return True
