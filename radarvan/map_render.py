"""Render a map image with player position overlays (name, general, team color)."""

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from .api_types import General, MapDataPayload, MapRenderPlayer

TEAM_COLORS: dict[int, str] = {
    1: "#2196F3",
    2: "#F44336",
    3: "#4CAF50",
    4: "#FF9800",
}


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_text_with_outline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    fill: str,
) -> None:
    x, y = xy
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        draw.text((x + dx, y + dy), text, font=font, fill="black", anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm")


def render_map(
    map_image_bytes: bytes,
    map_data: MapDataPayload,
    players: list[MapRenderPlayer],
) -> bytes:
    img = Image.open(BytesIO(map_image_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    width, height = img.size

    starts_by_num = {s.player_number: s for s in map_data.player_starts}
    radius = max(14, min(width, height) // 40)
    ring_width = max(3, radius // 4)
    label_font = _font(max(12, radius))
    number_font = _font(max(14, int(radius * 1.2)))

    for p in players:
        start = starts_by_num.get(p.position_number)
        if start is None:
            continue
        px = (start.x / map_data.extent.width) * width
        py = (1 - start.y / map_data.extent.height) * height
        team_color = TEAM_COLORS.get(p.team, "#FFFFFF")

        draw.ellipse(
            (px - radius, py - radius, px + radius, py + radius),
            fill="#212121",
            outline=team_color,
            width=ring_width,
        )
        _draw_text_with_outline(
            draw, (px, py), str(p.position_number), number_font, "white"
        )
        _draw_text_with_outline(
            draw, (px, py - radius - radius * 0.7), p.name, label_font, team_color
        )
        _draw_text_with_outline(
            draw,
            (px, py + radius + radius * 0.7),
            General(p.general).name,
            label_font,
            team_color,
        )

    out = BytesIO()
    img.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
