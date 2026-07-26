import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 720
HEIGHT = 440
SCALE = 2


def _font(size: int) -> ImageFont.FreeTypeFont:
    candidates = (
        Path("/System/Library/Fonts/SFNS.ttf"),
        Path("/System/Library/Fonts/HelveticaNeue.ttc"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size * SCALE)
    return ImageFont.load_default(size=size * SCALE)


def _centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
) -> None:
    bounds = draw.textbbox((0, 0), text, font=font)
    text_width = bounds[2] - bounds[0]
    draw.text(
        ((WIDTH * SCALE - text_width) / 2, y * SCALE),
        text,
        font=font,
        fill=fill,
    )


def create_background(output_path: Path) -> None:
    width = WIDTH * SCALE
    height = HEIGHT * SCALE
    image = Image.new("RGBA", (width, height))
    pixels = image.load()

    top_color = (22, 24, 30)
    bottom_color = (32, 36, 44)
    for y in range(height):
        progress = y / max(1, height - 1)
        for x in range(width):
            distance_x = abs(x - width / 2) / (width / 2)
            distance_y = abs(y - height / 2) / (height / 2)
            vignette = min(11, int((distance_x**2 + distance_y**2) * 6))
            pixels[x, y] = (
                max(
                    0,
                    int(top_color[0] * (1 - progress) + bottom_color[0] * progress)
                    - vignette,
                ),
                max(
                    0,
                    int(top_color[1] * (1 - progress) + bottom_color[1] * progress)
                    - vignette,
                ),
                max(
                    0,
                    int(top_color[2] * (1 - progress) + bottom_color[2] * progress)
                    - vignette,
                ),
                255,
            )

    draw = ImageDraw.Draw(image)
    _centered_text(
        draw,
        "MOVE TO APPLICATIONS",
        42,
        _font(25),
        (244, 245, 247, 255),
    )
    _centered_text(
        draw,
        "Drag the app into the Applications folder",
        78,
        _font(13),
        (158, 163, 173, 255),
    )

    arrow_y = 222 * SCALE
    start_x = 305 * SCALE
    shaft_end_x = 410 * SCALE
    tip_x = 454 * SCALE
    shadow_color = (0, 0, 0, 90)
    arrow_color = (151, 157, 168, 255)

    draw.line(
        (start_x, arrow_y + 4 * SCALE, shaft_end_x, arrow_y + 4 * SCALE),
        fill=shadow_color,
        width=10 * SCALE,
    )
    draw.polygon(
        (
            (shaft_end_x, arrow_y - 24 * SCALE + 4 * SCALE),
            (tip_x, arrow_y + 4 * SCALE),
            (shaft_end_x, arrow_y + 24 * SCALE + 4 * SCALE),
        ),
        fill=shadow_color,
    )
    draw.line(
        (start_x, arrow_y, shaft_end_x, arrow_y),
        fill=arrow_color,
        width=10 * SCALE,
    )
    draw.polygon(
        (
            (shaft_end_x, arrow_y - 24 * SCALE),
            (tip_x, arrow_y),
            (shaft_end_x, arrow_y + 24 * SCALE),
        ),
        fill=arrow_color,
    )

    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, "PNG", optimize=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: create_dmg_background.py OUTPUT.png")
    create_background(Path(sys.argv[1]))
