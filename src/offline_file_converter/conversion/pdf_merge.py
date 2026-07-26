from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import uuid4

import pikepdf


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
        with pikepdf.Pdf.new() as combined_pdf:
            for index, source_path in enumerate(paths):
                with pikepdf.Pdf.open(source_path) as source_pdf:
                    if not source_pdf.pages:
                        raise ValueError(
                            f"PDF не содержит страниц: {source_path.name}"
                        )
                    combined_pdf.pages.extend(source_pdf.pages)
                progress_callback(index + 1, len(paths))

            combined_pdf.save(
                temporary_output,
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

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
