"""Generate the local Home Assistant brand icon (requires Pillow)."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def make_icon(size: int = 1024) -> Image.Image:
    scale = size / 1024

    def box(coords):
        return tuple(round(value * scale) for value in coords)

    canvas = Image.new("RGBA", (size, size))
    pixels = canvas.load()
    for y in range(size):
        for x in range(size):
            blend = (x / size * 0.3 + y / size * 0.7)
            pixels[x, y] = (
                round(12 + 10 * blend),
                round(27 + 26 * blend),
                round(49 + 40 * blend),
                255,
            )

    mask = Image.new("L", (size, size))
    ImageDraw.Draw(mask).rounded_rectangle(box((0, 0, 1024, 1024)), radius=round(212 * scale), fill=255)
    canvas.putalpha(mask)

    glow = Image.new("RGBA", (size, size))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(box((176, 152, 848, 824)), fill=(30, 216, 206, 95))
    glow = glow.filter(ImageFilter.GaussianBlur(round(78 * scale)))
    canvas = Image.alpha_composite(canvas, glow)
    canvas.putalpha(mask)

    draw = ImageDraw.Draw(canvas)
    # A speech bubble also reads as a room/device command path at small sizes.
    draw.rounded_rectangle(box((176, 184, 848, 754)), radius=round(166 * scale), fill=(38, 201, 199), outline=(148, 248, 229), width=round(10 * scale))
    draw.rounded_rectangle(box((208, 216, 816, 722)), radius=round(139 * scale), fill=(17, 57, 81))
    draw.polygon([box((330, 700)), box((370, 834)), box((506, 714))], fill=(38, 201, 199))
    draw.polygon([box((363, 697)), box((388, 780)), box((480, 709))], fill=(17, 57, 81))

    # Three clear audio bars with a small central emphasis.
    draw.rounded_rectangle(box((327, 397, 393, 555)), radius=round(32 * scale), fill=(106, 238, 225))
    draw.rounded_rectangle(box((446, 329, 512, 623)), radius=round(32 * scale), fill=(248, 253, 253))
    draw.rounded_rectangle(box((565, 374, 631, 579)), radius=round(32 * scale), fill=(106, 238, 225))
    draw.ellipse(box((666, 324, 704, 362)), fill=(248, 253, 253))
    return canvas


if __name__ == "__main__":
    output = Path(__file__).resolve().parents[1] / "custom_components" / "universal_llm_assist" / "brand"
    output.mkdir(parents=True, exist_ok=True)
    icon = make_icon()
    icon.resize((512, 512), Image.Resampling.LANCZOS).save(output / "icon@2x.png")
    icon.resize((256, 256), Image.Resampling.LANCZOS).save(output / "icon.png")
