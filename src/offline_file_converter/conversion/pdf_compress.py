from collections.abc import Callable
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from uuid import uuid4

import pypdfium2 as pdfium
from pypdf import PdfReader, PdfWriter

from offline_file_converter.pdfium_runtime import PDFIUM_LOCK


ProgressCallback = Callable[[int, int], None]
HIGH_QUALITY_DPI = 300
HIGH_QUALITY_JPEG_QUALITY = 95

RASTER_PROFILES = (
    (200, 90),
    (180, 85),
    (160, 80),
    (140, 75),
    (120, 70),
    (110, 65),
    (100, 60),
    (90, 55),
    (80, 50),
    (70, 45),
    (60, 40),
    (54, 35),
    (48, 30),
)


def compress_pdf_with_high_quality(
    path: Path,
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    destination = output_directory or path.parent
    output_path = _available_output_path(destination, path.stem)
    temporary_output = output_path.with_name(
        f".{output_path.name}.{uuid4().hex}.tmp"
    )

    try:
        with TemporaryDirectory(prefix="offline-file-converter-") as temporary_dir:
            temporary_root = Path(temporary_dir)
            optimized_candidate = temporary_root / "optimized.pdf"
            source_pdf = PdfReader(str(path))
            if not source_pdf.pages:
                raise ValueError("PDF не содержит страниц.")
            _save_optimized_pdf(source_pdf, optimized_candidate)

            with PDFIUM_LOCK:
                document = pdfium.PdfDocument(str(path))
                try:
                    page_count = len(document)
                    if page_count < 1:
                        raise ValueError("PDF не содержит страниц.")

                    total_steps = 1 + page_count
                    progress_callback(1, total_steps)
                    high_quality_candidate = (
                        temporary_root / "high-quality.pdf"
                    )
                    _rasterize_pdf(
                        document,
                        high_quality_candidate,
                        HIGH_QUALITY_DPI,
                        HIGH_QUALITY_JPEG_QUALITY,
                        1,
                        total_steps,
                        progress_callback,
                        temporary_root,
                    )
                finally:
                    document.close()

            smallest_source = min(
                (path, optimized_candidate, high_quality_candidate),
                key=lambda candidate: candidate.stat().st_size,
            )
            copyfile(smallest_source, temporary_output)

        temporary_output.replace(output_path)
        return [output_path]
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise


def compress_pdf_file(
    path: Path,
    target_size_bytes: int,
    minimum_quality: int,
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    if target_size_bytes < 1:
        raise ValueError("Целевой размер должен быть больше нуля.")

    profiles = tuple(
        profile
        for profile in RASTER_PROFILES
        if profile[1] >= minimum_quality
    )
    if not profiles:
        raise ValueError("Неизвестный предел качества сжатия PDF.")

    destination = output_directory or path.parent
    output_path = _available_output_path(destination, path.stem)
    temporary_output = output_path.with_name(
        f".{output_path.name}.{uuid4().hex}.tmp"
    )

    try:
        if path.stat().st_size <= target_size_bytes:
            copyfile(path, temporary_output)
            progress_callback(1, 1)
            temporary_output.replace(output_path)
            return [output_path]

        with TemporaryDirectory(prefix="offline-file-converter-") as temporary_dir:
            temporary_root = Path(temporary_dir)
            lossless_candidate = temporary_root / "lossless.pdf"
            source_pdf = PdfReader(str(path))
            if not source_pdf.pages:
                raise ValueError("PDF не содержит страниц.")
            _save_optimized_pdf(source_pdf, lossless_candidate)

            if lossless_candidate.stat().st_size <= target_size_bytes:
                copyfile(lossless_candidate, temporary_output)
                progress_callback(1, 1)
                temporary_output.replace(output_path)
                return [output_path]

            with PDFIUM_LOCK:
                document = pdfium.PdfDocument(str(path))
                try:
                    page_count = len(document)
                    if page_count < 1:
                        raise ValueError("PDF не содержит страниц.")

                    total_steps = 1 + page_count * len(profiles)
                    progress_callback(1, total_steps)
                    smallest_size = lossless_candidate.stat().st_size
                    smallest_candidate = lossless_candidate

                    for profile_index, (dpi, quality) in enumerate(
                        profiles
                    ):
                        candidate = temporary_root / (
                            f"raster-{dpi}-{quality}.pdf"
                        )
                        _rasterize_pdf(
                            document,
                            candidate,
                            dpi,
                            quality,
                            1 + profile_index * page_count,
                            total_steps,
                            progress_callback,
                            temporary_root,
                        )
                        candidate_size = candidate.stat().st_size
                        if candidate_size < smallest_size:
                            smallest_size = candidate_size
                            smallest_candidate = candidate
                        if candidate_size <= target_size_bytes:
                            copyfile(candidate, temporary_output)
                            temporary_output.replace(output_path)
                            return [output_path]

                    copyfile(smallest_candidate, temporary_output)
                    temporary_output.replace(output_path)
                    return [output_path]
                finally:
                    document.close()
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise


def _rasterize_pdf(
    document: pdfium.PdfDocument,
    output_path: Path,
    dpi: int,
    quality: int,
    completed_before_profile: int,
    total_steps: int,
    progress_callback: ProgressCallback,
    temporary_root: Path,
) -> None:
    compressed_pdf = PdfWriter()
    for page_index in range(len(document)):
        page = document[page_index]
        try:
            bitmap = page.render(scale=dpi / 72)
            try:
                rendered_image = bitmap.to_pil()
                image = rendered_image.convert("RGB")
                try:
                    page_pdf_path = temporary_root / (
                        f"page-{dpi}-{quality}-{page_index}.pdf"
                    )
                    image.save(
                        page_pdf_path,
                        format="PDF",
                        resolution=dpi,
                        quality=quality,
                        optimize=True,
                    )
                    page_pdf = PdfReader(str(page_pdf_path))
                    compressed_pdf.append(page_pdf)
                finally:
                    image.close()
                    rendered_image.close()
            finally:
                bitmap.close()
        finally:
            page.close()

        progress_callback(
            completed_before_profile + page_index + 1,
            total_steps,
        )

    _write_optimized_writer(compressed_pdf, output_path)


def _save_optimized_pdf(
    source_pdf: PdfReader,
    output_path: Path,
) -> None:
    writer = PdfWriter()
    writer.clone_document_from_reader(source_pdf)
    _write_optimized_writer(writer, output_path)


def _write_optimized_writer(
    writer: PdfWriter,
    output_path: Path,
) -> None:
    for page in writer.pages:
        page.compress_content_streams()
    writer.compress_identical_objects(
        remove_duplicates=True,
        remove_unreferenced=True,
    )
    with output_path.open("wb") as output_file:
        writer.write(output_file)


def _available_output_path(destination: Path, source_stem: str) -> Path:
    version = 1
    while True:
        suffix = "" if version == 1 else f"_{version}"
        candidate = destination / f"{source_stem}_compressed{suffix}.pdf"
        if not candidate.exists():
            return candidate
        version += 1
