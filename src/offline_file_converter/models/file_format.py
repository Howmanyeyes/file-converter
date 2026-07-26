from pathlib import Path
from typing import Literal, TypeAlias
from zipfile import BadZipFile, ZipFile


FileFormat: TypeAlias = Literal[
    "pdf",
    "png",
    "jpeg",
    "word",
    "powerpoint",
]

PDF_SIGNATURE = b"%PDF-"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"
COMPOUND_DOCUMENT_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def detect_file_format(path: Path) -> FileFormat | None:
    try:
        with path.open("rb") as source:
            header = source.read(1024)
    except OSError:
        return None

    if header.startswith(PNG_SIGNATURE):
        return "png"
    if header.startswith(JPEG_SIGNATURE):
        return "jpeg"
    if PDF_SIGNATURE in header:
        return "pdf"
    office_format = _detect_office_format(path, header)
    if office_format is not None:
        return office_format
    return None


def _detect_office_format(
    path: Path,
    header: bytes,
) -> FileFormat | None:
    suffix = path.suffix.lower()
    if header.startswith(b"PK\x03\x04"):
        try:
            with ZipFile(path) as package:
                package_entries = set(package.namelist())
        except (OSError, BadZipFile):
            return None
        if "word/document.xml" in package_entries:
            return "word"
        if "ppt/presentation.xml" in package_entries:
            return "powerpoint"
        return None

    if not header.startswith(COMPOUND_DOCUMENT_SIGNATURE):
        return None
    if suffix == ".doc":
        return "word"
    if suffix == ".ppt":
        return "powerpoint"
    return None
