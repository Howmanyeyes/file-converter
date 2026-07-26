import os
from importlib.resources import files
from typing import Literal, TypeAlias


AppEdition: TypeAlias = Literal["full", "lite"]
EDITION_ENVIRONMENT_VARIABLE = "OFFLINE_FILE_CONVERTER_EDITION"


def _read_edition() -> AppEdition:
    environment_value = os.environ.get(
        EDITION_ENVIRONMENT_VARIABLE,
        "",
    ).strip().lower()
    if environment_value in {"full", "lite"}:
        return environment_value

    try:
        bundled_value = (
            files("offline_file_converter.resources")
            .joinpath("edition.txt")
            .read_text(encoding="utf-8")
            .strip()
            .lower()
        )
    except (FileNotFoundError, OSError):
        return "full"

    if bundled_value == "lite":
        return "lite"
    return "full"


APP_EDITION = _read_edition()
OFFICE_SUPPORT_ENABLED = APP_EDITION == "full"
