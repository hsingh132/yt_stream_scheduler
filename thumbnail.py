"""Thumbnail generator: draws the samagam location and date onto the
blank template PNG, in the same spot every time.

Box positions/colors below were read directly off the Canva template
(Advanced position panel + sampled text color from the reference export).
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).parent
TEMPLATE_PATH = BASE_DIR / "template_blank.png"
OUTPUT_DIR = BASE_DIR / "thumbnails"

LOCATION_FONT_PATH = BASE_DIR / "fonts" / "PlayfairDisplay-Variable.ttf"
LOCATION_FONT_VARIATION = b"Bold"
DATE_FONT_PATH = BASE_DIR / "fonts" / "AbrilFatface-Regular.ttf"


@dataclass
class TextBox:
    x: float
    y: float
    width: float
    height: float
    color: tuple[int, int, int]
    max_font_size: int
    min_font_size: int = 18


# y/height match the actual gray band in the background image (427-574px),
# not the tighter text-element box Canva reports, so the text centers in
# the visible stripe rather than a sub-region of it.
# Font size sized a bit below what would exactly fill "San Francisco, CA" so
# longer names (e.g. "Fort Lauderdale, FL") still have room to shrink into.
LOCATION_BOX = TextBox(x=23.5, y=427, width=674.8, height=147, color=(2, 12, 70), max_font_size=46)
DATE_BOX = TextBox(x=23.5, y=604.1, width=582.5, height=39.4, color=(37, 16, 163), max_font_size=30)


def _load_font(path: Path, size: int, variation: bytes | None = None) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(path), size)
    if variation:
        font.set_variation_by_name(variation)
    return font


def _fit_font(draw: ImageDraw.ImageDraw, text: str, path: Path, box: TextBox, variation: bytes | None = None) -> ImageFont.FreeTypeFont:
    size = box.max_font_size
    while size > box.min_font_size:
        font = _load_font(path, size, variation)
        width = draw.textbbox((0, 0), text, font=font)[2]
        if width <= box.width:
            return font
        size -= 1
    return _load_font(path, box.min_font_size, variation)


def _draw_left_vcenter(draw: ImageDraw.ImageDraw, text: str, box: TextBox, font: ImageFont.FreeTypeFont) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_height = bottom - top
    y = box.y + (box.height - text_height) / 2 - top
    draw.text((box.x, y), text, font=font, fill=box.color)


def format_location(city: str, state: str) -> str:
    return f"{city}, {state}".upper() if state else city.upper()


def format_date_range(start: date, end: date) -> str:
    start_str = f"{start.day} {start:%B}"
    end_str = f"{end.day} {end:%B} {end.year}"
    return f"{start_str} - {end_str}".upper()


def generate_thumbnail(city: str, state: str, start: date, end: date, output_path: Path | None = None) -> Path:
    print(f"[thumbnail] Generating thumbnail for {city}, {state} ({start} - {end})")

    image = Image.open(TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(image)

    location_text = format_location(city, state)
    date_text = format_date_range(start, end)

    location_font = _fit_font(draw, location_text, LOCATION_FONT_PATH, LOCATION_BOX, LOCATION_FONT_VARIATION)
    date_font = _fit_font(draw, date_text, DATE_FONT_PATH, DATE_BOX)

    _draw_left_vcenter(draw, location_text, LOCATION_BOX, location_font)
    _draw_left_vcenter(draw, date_text, DATE_BOX, date_font)

    OUTPUT_DIR.mkdir(exist_ok=True)
    if output_path is None:
        slug = f"{city}-{state}-{start}".replace(" ", "_").replace(",", "")
        output_path = OUTPUT_DIR / f"{slug}.png"

    image.save(output_path)
    print(f"[thumbnail] Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    # Quick test against the known reference thumbnail (San Francisco, CA).
    generate_thumbnail("San Francisco", "CA", date(2026, 7, 2), date(2026, 7, 5), BASE_DIR / "thumbnails" / "test_san_francisco.png")
