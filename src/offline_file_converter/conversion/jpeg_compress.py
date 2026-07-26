from collections.abc import Callable
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from uuid import uuid4

from PIL import Image


ProgressCallback = Callable[[int, int], None]
QUALITY_PROFILES = tuple(range(95, 29, -5))


def compress_jpeg_with_high_quality(
    path: Path,
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    return _compress_jpeg(
        path,
        95,
        None,
        output_directory,
        progress_callback,
    )


def compress_jpeg_file(
    path: Path,
    target_size_bytes: int,
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    if target_size_bytes < 1:
        raise ValueError("Целевой размер должен быть больше нуля.")
    return _compress_jpeg(
        path,
        None,
        target_size_bytes,
        output_directory,
        progress_callback,
    )


def _compress_jpeg(
    path: Path,
    fixed_quality: int | None,
    target_size_bytes: int | None,
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    destination = output_directory or path.parent
    extension = _jpeg_extension(path)
    output_path = _available_output_path(
        destination,
        path.stem,
        extension,
    )
    temporary_output = output_path.with_name(
        f".{output_path.name}.{uuid4().hex}.tmp"
    )

    try:
        original_size = path.stat().st_size
        if target_size_bytes is not None and original_size <= target_size_bytes:
            copyfile(path, temporary_output)
            progress_callback(1, 1)
            temporary_output.replace(output_path)
            return [output_path]

        profiles = (
            (fixed_quality,)
            if fixed_quality is not None
            else QUALITY_PROFILES
        )
        with TemporaryDirectory(prefix="offline-file-converter-") as temporary_dir:
            temporary_root = Path(temporary_dir)
            with Image.open(path) as source_image:
                source_image.load()
                resolution = _image_dpi(source_image)
                image = source_image.convert("RGB")
                try:
                    smallest_candidate = path
                    smallest_size = original_size
                    for index, quality in enumerate(profiles, start=1):
                        candidate = temporary_root / (
                            f"quality-{quality}.{extension}"
                        )
                        image.save(
                            candidate,
                            format="JPEG",
                            quality=quality,
                            optimize=True,
                            progressive=True,
                            dpi=resolution,
                        )
                        candidate_size = candidate.stat().st_size
                        if candidate_size < smallest_size:
                            smallest_candidate = candidate
                            smallest_size = candidate_size
                        progress_callback(index, len(profiles))
                        if (
                            target_size_bytes is not None
                            and candidate_size <= target_size_bytes
                        ):
                            smallest_candidate = candidate
                            break
                finally:
                    image.close()

            copyfile(smallest_candidate, temporary_output)

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
            destination / f"{source_stem}_compressed{suffix}.{extension}"
        )
        if not candidate.exists():
            return candidate
        version += 1
