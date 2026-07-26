from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import uuid4

from PIL import Image


ProgressCallback = Callable[[int, int], None]


def convert_jpeg_files_to_png(
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
            )
            temporary_path = output_path.with_name(
                f".{output_path.name}.{uuid4().hex}.tmp"
            )
            temporary_outputs.append(temporary_path)

            with Image.open(source_path) as source_image:
                source_image.load()
                image = source_image.convert("RGB")
                try:
                    image.save(
                        temporary_path,
                        format="PNG",
                        optimize=True,
                        compress_level=9,
                        dpi=_image_dpi(source_image),
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


def _available_output_path(destination: Path, source_stem: str) -> Path:
    version = 1
    while True:
        suffix = "" if version == 1 else f"_{version}"
        candidate = destination / f"{source_stem}{suffix}.png"
        if not candidate.exists():
            return candidate
        version += 1
