from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from offline_file_converter.models.file_format import FileFormat


@dataclass(slots=True)
class SelectedFile:
    path: Path
    order: int
    detected_format: FileFormat
    id: str = field(default_factory=lambda: uuid4().hex)
