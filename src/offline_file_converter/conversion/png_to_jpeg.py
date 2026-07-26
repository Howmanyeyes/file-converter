from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import uuid4

from PIL import Image


ProgressCallback = Callable[[int, int], None]


def convert_png_files_to_jpeg(
    paths: Sequence[Path],
    quality: int,
    extension: str,
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    if extension not in {"jpg", "jpeg"}:
        raise ValueError("Неподдерживаемое расширение JPEG.")

    created_outputs: list[Path] = []
    temporary_outputs: list[Path] = []

    try:
        for index, source_path in enumerate(paths):
            destination = output_directory or source_path.parent
            output_path = _available_output_path(
                destination,
                source_path.stem,
                extension,
            )
            temporary_path = output_path.with_name(
                f".{output_path.name}.{uuid4().hex}.tmp"
            )
            temporary_outputs.append(temporary_path)

            with Image.open(source_path) as source_image:
                source_image.load()
                dpi = _image_dpi(source_image)
                image = _flatten_to_rgb(source_image)
                try:
                    image.save(
                        temporary_path,
                        format="JPEG",
                        quality=quality,
                        optimize=True,
                        progressive=True,
                        dpi=dpi,
                    )
                finally:
                    image.close()

            temporary_path.replace(output_path)
            temporary_outputs.remove(temporary_path)
            created_outputs.append(output_path)
            progress_callback(index + 1, len(paths))

        return created_outputs
    except Exception:
        for temporary_path in temporary_outputs:
            temporary_path.unlink(missing_ok=True)
        for output_path in created_outputs:
            output_path.unlink(missing_ok=True)
        raise


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


def _image_dpi(source_image: Image.Image) -> tuple[float, float]:
    dpi = source_image.info.get("dpi", (96, 96))
    try:
        horizontal = float(dpi[0])
        vertical = float(dpi[1])
    except (TypeError, ValueError, IndexError):
        return (96, 96)
    if horizontal <= 0 or vertical <= 0:
        return (96, 96)
    return (horizontal, vertical)


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
