from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader, PdfWriter


ProgressCallback = Callable[[int, int], None]


def merge_pdf_files(
    paths: Sequence[Path],
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    if len(paths) < 2:
        raise ValueError("Для объединения выберите минимум два PDF.")

    destination = output_directory or paths[0].parent
    output_path = _available_output_path(destination, paths[0].stem)
    temporary_output = output_path.with_name(
        f".{output_path.name}.{uuid4().hex}.tmp"
    )

    try:
        combined_pdf = PdfWriter()
        for index, source_path in enumerate(paths):
            source_pdf = PdfReader(str(source_path))
            if not source_pdf.pages:
                raise ValueError(
                    f"PDF не содержит страниц: {source_path.name}"
                )
            combined_pdf.append(source_pdf)
            progress_callback(index + 1, len(paths))

        combined_pdf.compress_identical_objects(
            remove_duplicates=True,
            remove_unreferenced=True,
        )
        with temporary_output.open("wb") as output_file:
            combined_pdf.write(output_file)

        temporary_output.replace(output_path)
        return [output_path]
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise


def _available_output_path(destination: Path, source_stem: str) -> Path:
    version = 1
    while True:
        suffix = "" if version == 1 else f"_{version}"
        candidate = destination / f"{source_stem}_combined{suffix}.pdf"
        if not candidate.exists():
            return candidate
        version += 1
