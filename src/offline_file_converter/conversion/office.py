from collections.abc import Callable, Sequence
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from uuid import uuid4

from offline_file_converter.conversion.pdf_to_jpeg import (
    convert_pdf_files_to_jpeg,
)
from offline_file_converter.conversion.pdf_to_png import (
    convert_pdf_files_to_png,
)
from offline_file_converter.office_runtime import (
    convert_office_document_to_pdf,
)


ProgressCallback = Callable[[int, int], None]


def convert_office_files_to_pdf(
    paths: Sequence[Path],
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    created_outputs: list[Path] = []
    temporary_outputs: list[Path] = []

    try:
        for index, source_path in enumerate(paths):
            destination = output_directory or source_path.parent
            output_path = _available_output_path(
                destination,
                source_path.stem,
                "pdf",
            )
            temporary_output = output_path.with_name(
                f".{output_path.name}.{uuid4().hex}.tmp"
            )
            temporary_outputs.append(temporary_output)

            with TemporaryDirectory(
                prefix="offline-file-converter-office-"
            ) as temporary_directory:
                converted_pdf = convert_office_document_to_pdf(
                    source_path,
                    Path(temporary_directory),
                )
                copyfile(converted_pdf, temporary_output)

            temporary_output.replace(output_path)
            temporary_outputs.remove(temporary_output)
            created_outputs.append(output_path)
            progress_callback(index + 1, len(paths))

        return created_outputs
    except Exception:
        for temporary_output in temporary_outputs:
            temporary_output.unlink(missing_ok=True)
        for output_path in created_outputs:
            output_path.unlink(missing_ok=True)
        raise


def convert_office_files_to_png(
    paths: Sequence[Path],
    dpi: int,
    output_directory: Path | None,
    export_mode: str,
    progress_callback: ProgressCallback,
) -> list[Path]:
    created_outputs: list[Path] = []
    try:
        for index, source_path in enumerate(paths):
            destination = output_directory or source_path.parent
            with TemporaryDirectory(
                prefix="offline-file-converter-office-"
            ) as temporary_directory:
                converted_pdf = convert_office_document_to_pdf(
                    source_path,
                    Path(temporary_directory),
                )
                outputs = convert_pdf_files_to_png(
                    (converted_pdf,),
                    dpi,
                    destination,
                    export_mode,
                    lambda _completed, _total: None,
                )
                created_outputs.extend(outputs)
            progress_callback(index + 1, len(paths))
        return created_outputs
    except Exception:
        for output_path in created_outputs:
            output_path.unlink(missing_ok=True)
        raise


def convert_office_files_to_jpeg(
    paths: Sequence[Path],
    dpi: int,
    quality: int,
    extension: str,
    output_directory: Path | None,
    export_mode: str,
    progress_callback: ProgressCallback,
) -> list[Path]:
    created_outputs: list[Path] = []
    try:
        for index, source_path in enumerate(paths):
            destination = output_directory or source_path.parent
            with TemporaryDirectory(
                prefix="offline-file-converter-office-"
            ) as temporary_directory:
                converted_pdf = convert_office_document_to_pdf(
                    source_path,
                    Path(temporary_directory),
                )
                outputs = convert_pdf_files_to_jpeg(
                    (converted_pdf,),
                    dpi,
                    quality,
                    extension,
                    destination,
                    export_mode,
                    lambda _completed, _total: None,
                )
                created_outputs.extend(outputs)
            progress_callback(index + 1, len(paths))
        return created_outputs
    except Exception:
        for output_path in created_outputs:
            output_path.unlink(missing_ok=True)
        raise


def _available_output_path(
    destination: Path,
    source_stem: str,
    extension: str,
) -> Path:
    version = 1
    while True:
        suffix = "" if version == 1 else f"_{version}"
        candidate = destination / f"{source_stem}{suffix}.{extension}"
        if not candidate.exists():
            return candidate
        version += 1
