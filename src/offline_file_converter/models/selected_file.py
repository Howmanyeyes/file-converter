from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4


@dataclass(slots=True)
class SelectedFile:
    path: Path
    order: int
    id: str = field(default_factory=lambda: uuid4().hex)
