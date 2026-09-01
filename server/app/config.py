from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    storage_root: Path
    production_root: Path | None = None
    max_upload_bytes: int = 250 * 1024 * 1024
