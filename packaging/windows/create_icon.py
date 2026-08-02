import sys
from pathlib import Path

from PIL import Image


ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def create_icon(source_path: Path, output_path: Path) -> None:
    with Image.open(source_path) as source_image:
        icon = source_image.convert("RGBA")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            icon.save(
                output_path,
                format="ICO",
                sizes=[(size, size) for size in ICON_SIZES],
            )
        finally:
            icon.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: create_icon.py SOURCE.png OUTPUT.ico")
    create_icon(Path(sys.argv[1]), Path(sys.argv[2]))
