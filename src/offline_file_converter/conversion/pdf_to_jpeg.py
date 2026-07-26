from collections.abc import Callable, Sequence
from math import ceil
from pathlib import Path
from uuid import uuid4

import pypdfium2 as pdfium
from PIL import Image

from offline_file_converter.pdfium_runtime import PDFIUM_LOCK


ProgressCallback = Callable[[int, int], None]


def convert_pdf_files_to_jpeg(
    paths: Sequence[Path],
    dpi: int,
    quality: int,
    extension: str,
    output_directory: Path | None,
    export_mode: str,
    progress_callback: ProgressCallback,
) -> list[Path]:
    created_outputs: list[Path] = []
    temporary_outputs: list[Path] = []

    if extension not in {"jpg", "jpeg"}:
        raise ValueError("Неподдерживаемое расширение JPEG.")
    if export_mode not in {"single", "separate"}:
        raise ValueError("Неподдерживаемый режим экспорта PDF.")

    try:
        with PDFIUM_LOCK:
            page_counts = [_read_page_count(path) for path in paths]
            total_pages = sum(page_counts)
            if total_pages == 0:
                raise ValueError("В выбранных PDF нет страниц.")

            completed_pages = 0
            for source_path, page_count in zip(paths, page_counts):
                output_count = (
                    1 if export_mode == "single" else page_count
                )
                output_paths = _available_output_paths(
                    source_path,
                    output_count,
                    extension,
                    output_directory,
                )
                document = pdfium.PdfDocument(str(source_path))
                try:
                    if export_mode == "single" and page_count > 1:
                        completed_pages = _render_combined_jpeg(
                            document,
                            page_count,
                            dpi,
                            quality,
                            output_paths[0],
                            temporary_outputs,
                            created_outputs,
                            completed_pages,
                            total_pages,
                            progress_callback,
                        )
                        continue

                    for page_index, output_path in enumerate(output_paths):
                        page = document[page_index]
                        try:
                            bitmap = page.render(scale=dpi / 72)
                            try:
                                rendered_image = bitmap.to_pil()
                                image = rendered_image.convert("RGB")
                                temporary_path = output_path.with_name(
                                    f".{output_path.name}.{uuid4().hex}.tmp"
                                )
                                temporary_outputs.append(temporary_path)
                                try:
                                    image.save(
                                        temporary_path,
                                        format="JPEG",
                                        quality=quality,
                                        optimize=True,
                                        progressive=True,
                                        dpi=(dpi, dpi),
                                    )
                                finally:
                                    image.close()
                                    rendered_image.close()

                                temporary_path.replace(output_path)
                                temporary_outputs.remove(temporary_path)
                                created_outputs.append(output_path)
                            finally:
                                bitmap.close()
                        finally:
                            page.close()

                        completed_pages += 1
                        progress_callback(completed_pages, total_pages)
                finally:
                    document.close()

        return created_outputs
    except Exception:
        for temporary_path in temporary_outputs:
            temporary_path.unlink(missing_ok=True)
        for output_path in created_outputs:
            output_path.unlink(missing_ok=True)
        raise


def _render_combined_jpeg(
    document: pdfium.PdfDocument,
    page_count: int,
    dpi: int,
    quality: int,
    output_path: Path,
    temporary_outputs: list[Path],
    created_outputs: list[Path],
    completed_pages: int,
    total_pages: int,
    progress_callback: ProgressCallback,
) -> int:
    scale = dpi / 72
    page_sizes: list[tuple[int, int]] = []
    for page_index in range(page_count):
        page = document[page_index]
        try:
            width, height = page.get_size()
            page_sizes.append((ceil(width * scale), ceil(height * scale)))
        finally:
            page.close()

    canvas = Image.new(
        "RGB",
        (max(width for width, _height in page_sizes), sum(
            height for _width, height in page_sizes
        )),
        "white",
    )
    try:
        y_position = 0
        for page_index, (_width, reserved_height) in enumerate(page_sizes):
            page = document[page_index]
            try:
                bitmap = page.render(scale=scale)
                try:
                    rendered_image = bitmap.to_pil()
                    page_image = rendered_image.convert("RGB")
                    try:
                        x_position = (canvas.width - page_image.width) // 2
                        canvas.paste(page_image, (x_position, y_position))
                    finally:
                        page_image.close()
                        rendered_image.close()
                finally:
                    bitmap.close()
            finally:
                page.close()

            y_position += reserved_height
            completed_pages += 1
            progress_callback(completed_pages, total_pages)

        temporary_path = output_path.with_name(
            f".{output_path.name}.{uuid4().hex}.tmp"
        )
        temporary_outputs.append(temporary_path)
        canvas.save(
            temporary_path,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
            dpi=(dpi, dpi),
        )
        temporary_path.replace(output_path)
        temporary_outputs.remove(temporary_path)
        created_outputs.append(output_path)
    finally:
        canvas.close()

    return completed_pages


def _read_page_count(path: Path) -> int:
    document = pdfium.PdfDocument(str(path))
    try:
        page_count = len(document)
        if page_count < 1:
            raise ValueError(f"PDF не содержит страниц: {path.name}")
        return page_count
    finally:
        document.close()


def _available_output_paths(
    source_path: Path,
    page_count: int,
    extension: str,
    output_directory: Path | None,
) -> list[Path]:
    number_width = max(3, len(str(page_count)))
    destination = output_directory or source_path.parent
    version = 1

    while True:
        collision_suffix = "" if version == 1 else f"_{version}"
        if page_count == 1:
            candidates = [
                destination.joinpath(
                    f"{source_path.stem}{collision_suffix}.{extension}"
                )
            ]
        else:
            candidates = [
                destination.joinpath(
                    f"{source_path.stem}_{page_number:0{number_width}d}"
                    f"{collision_suffix}.{extension}"
                )
                for page_number in range(1, page_count + 1)
            ]
        if not any(candidate.exists() for candidate in candidates):
            return candidates
        version += 1
