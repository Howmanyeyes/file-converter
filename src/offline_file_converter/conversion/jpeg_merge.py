from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import uuid4

from PIL import Image


ProgressCallback = Callable[[int, int], None]


def merge_jpeg_files(
    paths: Sequence[Path],
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    if len(paths) < 2:
        raise ValueError("Для объединения выберите минимум два JPEG.")

    destination = output_directory or paths[0].parent
    extension = _jpeg_extension(paths[0])
    output_path = _available_output_path(
        destination,
        paths[0].stem,
        extension,
    )
    temporary_output = output_path.with_name(
        f".{output_path.name}.{uuid4().hex}.tmp"
    )

    try:
        sizes: list[tuple[int, int]] = []
        resolution = (96.0, 96.0)
        for index, path in enumerate(paths):
            with Image.open(path) as image:
                sizes.append(image.size)
                if index == 0:
                    resolution = _image_dpi(image)

        canvas_width = max(width for width, _height in sizes)
        canvas_height = sum(height for _width, height in sizes)
        canvas = Image.new(
            "RGB",
            (canvas_width, canvas_height),
            "white",
        )

        try:
            y_position = 0
            for index, (path, (_width, reserved_height)) in enumerate(
                zip(paths, sizes),
                start=1,
            ):
                with Image.open(path) as source_image:
                    source_image.load()
                    image = source_image.convert("RGB")
                    try:
                        x_position = (canvas_width - image.width) // 2
                        canvas.paste(image, (x_position, y_position))
                    finally:
                        image.close()

                y_position += reserved_height
                progress_callback(index, len(paths))

            canvas.save(
                temporary_output,
                format="JPEG",
                quality=95,
                optimize=True,
                progressive=True,
                dpi=resolution,
            )
        finally:
            canvas.close()

        temporary_output.replace(output_path)
        return [output_path]
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise


def _image_dpi(image: Image.Image) -> tuple[float, float]:
    dpi = image.info.get("dpi", (96, 96))
    try:
        horizontal = float(dpi[0])
        vertical = float(dpi[1])
    except (TypeError, ValueError, IndexError):
        return (96, 96)
    if horizontal <= 0 or vertical <= 0:
        return (96, 96)
    return (horizontal, vertical)


def _jpeg_extension(path: Path) -> str:
    return "jpeg" if path.suffix.lower() == ".jpeg" else "jpg"


def _available_output_path(
    destination: Path,
    source_stem: str,
    extension: str,
) -> Path:
    version = 1
    while True:
        suffix = "" if version == 1 else f"_{version}"
        candidate = (
            destination / f"{source_stem}_combined{suffix}.{extension}"
        )
        if not candidate.exists():
            return candidate
        version += 1
