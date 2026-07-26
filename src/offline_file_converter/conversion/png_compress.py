from collections.abc import Callable
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from uuid import uuid4

from PIL import Image


ProgressCallback = Callable[[int, int], None]
COLOR_PROFILES = (256, 128, 64, 32, 16)


def compress_png_losslessly(
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
            optimized_candidate = Path(temporary_dir) / "optimized.png"
            with Image.open(path) as source_image:
                source_image.load()
                _save_png(
                    source_image,
                    optimized_candidate,
                    _image_dpi(source_image),
                    source_image.info.get("icc_profile"),
                )

            smallest_source = (
                optimized_candidate
                if optimized_candidate.stat().st_size < path.stat().st_size
                else path
            )
            copyfile(smallest_source, temporary_output)

        progress_callback(1, 1)
        temporary_output.replace(output_path)
        return [output_path]
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise


def compress_png_file(
    path: Path,
    target_size_bytes: int,
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    if target_size_bytes < 1:
        raise ValueError("Целевой размер должен быть больше нуля.")

    destination = output_directory or path.parent
    output_path = _available_output_path(destination, path.stem)
    temporary_output = output_path.with_name(
        f".{output_path.name}.{uuid4().hex}.tmp"
    )

    try:
        original_size = path.stat().st_size
        if original_size <= target_size_bytes:
            copyfile(path, temporary_output)
            progress_callback(1, 1)
            temporary_output.replace(output_path)
            return [output_path]

        with TemporaryDirectory(prefix="offline-file-converter-") as temporary_dir:
            temporary_root = Path(temporary_dir)
            with Image.open(path) as source_image:
                source_image.load()
                resolution = _image_dpi(source_image)
                icc_profile = source_image.info.get("icc_profile")
                has_transparency = (
                    "A" in source_image.getbands()
                    or "transparency" in source_image.info
                )

                lossless_candidate = temporary_root / "lossless.png"
                _save_png(
                    source_image,
                    lossless_candidate,
                    resolution,
                    icc_profile,
                )
                progress_callback(1, 1 + len(COLOR_PROFILES))

                lossless_size = lossless_candidate.stat().st_size
                if lossless_size <= target_size_bytes:
                    copyfile(lossless_candidate, temporary_output)
                    temporary_output.replace(output_path)
                    return [output_path]

                smallest_candidate = (
                    lossless_candidate
                    if lossless_size < original_size
                    else path
                )
                smallest_size = min(lossless_size, original_size)
                base_image = source_image.convert(
                    "RGBA" if has_transparency else "RGB"
                )
                try:
                    method = (
                        Image.Quantize.FASTOCTREE
                        if has_transparency
                        else Image.Quantize.MEDIANCUT
                    )
                    for index, color_count in enumerate(
                        COLOR_PROFILES,
                        start=2,
                    ):
                        candidate = temporary_root / (
                            f"palette-{color_count}.png"
                        )
                        quantized_image = base_image.quantize(
                            colors=color_count,
                            method=method,
                            dither=Image.Dither.FLOYDSTEINBERG,
                        )
                        try:
                            _save_png(
                                quantized_image,
                                candidate,
                                resolution,
                                icc_profile,
                            )
                        finally:
                            quantized_image.close()

                        candidate_size = candidate.stat().st_size
                        if candidate_size < smallest_size:
                            smallest_size = candidate_size
                            smallest_candidate = candidate
                        progress_callback(
                            index,
                            1 + len(COLOR_PROFILES),
                        )
                        if candidate_size <= target_size_bytes:
                            copyfile(candidate, temporary_output)
                            temporary_output.replace(output_path)
                            return [output_path]
                finally:
                    base_image.close()

                copyfile(smallest_candidate, temporary_output)
                temporary_output.replace(output_path)
                return [output_path]
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise


def _save_png(
    image: Image.Image,
    path: Path,
    resolution: tuple[float, float],
    icc_profile: bytes | None,
) -> None:
    options: dict[str, object] = {
        "format": "PNG",
        "optimize": True,
        "compress_level": 9,
        "dpi": resolution,
    }
    if icc_profile is not None:
        options["icc_profile"] = icc_profile
    image.save(path, **options)


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
        candidate = destination / f"{source_stem}_compressed{suffix}.png"
        if not candidate.exists():
            return candidate
        version += 1
