from collections.abc import Callable, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from PIL import Image
from pypdf import PdfReader, PdfWriter


ProgressCallback = Callable[[int, int], None]


def convert_png_files_to_pdf(
    paths: Sequence[Path],
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    if not paths:
        raise ValueError("Не выбраны PNG-файлы.")

    destination = output_directory or paths[0].parent
    output_path = _available_output_path(destination, paths[0].stem)
    temporary_output = output_path.with_name(
        f".{output_path.name}.{uuid4().hex}.tmp"
    )

    try:
        with TemporaryDirectory(prefix="offline-file-converter-") as temporary_dir:
            combined_pdf = PdfWriter()
            for index, source_path in enumerate(paths):
                page_pdf_path = Path(temporary_dir) / f"page-{index}.pdf"
                _save_png_as_pdf_page(source_path, page_pdf_path)
                page_pdf = PdfReader(str(page_pdf_path))
                combined_pdf.append(page_pdf)
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
        output_path.unlink(missing_ok=True)
        raise


def _save_png_as_pdf_page(source_path: Path, output_path: Path) -> None:
    with Image.open(source_path) as source_image:
        source_image.load()
        resolution = _image_resolution(source_image)
        image = _flatten_to_rgb(source_image)
        try:
            image.save(
                output_path,
                format="PDF",
                resolution=resolution,
                quality=95,
            )
        finally:
            image.close()


def _flatten_to_rgb(source_image: Image.Image) -> Image.Image:
    if (
        "A" not in source_image.getbands()
        and "transparency" not in source_image.info
    ):
        return source_image.convert("RGB")

    rgba_image = source_image.convert("RGBA")
    try:
        background = Image.new("RGB", rgba_image.size, "white")
        background.paste(rgba_image, mask=rgba_image.getchannel("A"))
        return background
    finally:
        rgba_image.close()


def _image_resolution(source_image: Image.Image) -> float:
    dpi = source_image.info.get("dpi", (96, 96))
    try:
        resolution = float(dpi[0])
    except (TypeError, ValueError, IndexError):
        return 96
    return resolution if resolution > 0 else 96


def _available_output_path(destination: Path, source_stem: str) -> Path:
    version = 1
    while True:
        suffix = "" if version == 1 else f"_{version}"
        candidate = destination / f"{source_stem}{suffix}.pdf"
        if not candidate.exists():
            return candidate
        version += 1
