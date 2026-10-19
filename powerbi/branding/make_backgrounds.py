"""
make_backgrounds.py — page backgrounds and a fictitious brand ("ROTA · Marketplace Analytics")
for the Power BI report. Pure Pillow drawing, no external assets.

Outputs (same folder):
  bg_1600x900.png    canvas used by build_pbip.py (16:9, matches the 1280x720 layout grid)
  bg_1600x1200.png   taller variants for scrolling pages, same header/footer
  bg_1600x2000.png
  logo_rota.png      wordmark on transparent background, light text (dark bands)
  logo_rota_dark.png wordmark on transparent background, dark text (README, slides)

Run:  python make_backgrounds.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
FONTS = Path("C:/Windows/Fonts")
BOLD, SEMI, REG, LIGHT = (FONTS / "segoeuib.ttf", FONTS / "seguisb.ttf",
                          FONTS / "segoeui.ttf", FONTS / "segoeuil.ttf")

NAVY = (26, 54, 93)
BLUE = (43, 108, 176)
SKY = (99, 179, 237)
PAGE = (247, 250, 252)
MUTED = (203, 213, 224)
FOOT = (160, 174, 192)
LINE = (226, 232, 240)
WHITE = (255, 255, 255)

BAND = 64          # must match BAND in build_pbip.py
BRAND = "ROTA"
TAGLINE = "Marketplace Analytics"
DATASET = "Olist Brazilian E-Commerce public dataset  ·  Jan 2017 – Aug 2018"
FOOTER = "Delivery Experience case  ·  Snowflake  →  Power BI (PBIP)  ·  versioned on GitHub"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def draw_mark(d: ImageDraw.ImageDraw, x: int, y: int, size: int, fg, accent) -> None:
    """Round badge with a route line and a destination pin."""
    r = size / 2
    d.ellipse([x, y, x + size, y + size], fill=fg)
    # route: a bent line from bottom-left to top-right inside the badge
    pts = [(x + size * 0.26, y + size * 0.72), (x + size * 0.46, y + size * 0.52),
           (x + size * 0.56, y + size * 0.60), (x + size * 0.74, y + size * 0.32)]
    d.line(pts, fill=NAVY if fg == WHITE else WHITE, width=max(2, size // 11), joint="curve")
    # origin dot and destination pin
    o = size * 0.07
    d.ellipse([pts[0][0] - o, pts[0][1] - o, pts[0][0] + o, pts[0][1] + o], fill=NAVY if fg == WHITE else WHITE)
    p = size * 0.11
    d.ellipse([pts[-1][0] - p, pts[-1][1] - p, pts[-1][0] + p, pts[-1][1] + p], fill=accent)


def draw_wordmark(d: ImageDraw.ImageDraw, x: int, y: int, h: int, light: bool) -> int:
    """Mark + BRAND + tagline. Returns the right edge."""
    fg, text, sub = (WHITE, WHITE, MUTED) if light else (NAVY, NAVY, (74, 85, 104))
    draw_mark(d, x, y, h, fg, SKY if light else BLUE)
    f1 = font(BOLD, int(h * 0.62))
    f2 = font(REG, int(h * 0.30))
    tx = x + h + int(h * 0.35)
    d.text((tx, y - int(h * 0.06)), BRAND, font=f1, fill=text)
    d.text((tx + 2, y + int(h * 0.60)), TAGLINE, font=f2, fill=sub)
    return tx + int(max(d.textlength(BRAND, font=f1), d.textlength(TAGLINE, font=f2)))


def background(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), PAGE)
    d = ImageDraw.Draw(img)
    # header band + accent line
    d.rectangle([0, 0, w, BAND], fill=NAVY)
    d.rectangle([0, BAND, w, BAND + 3], fill=BLUE)
    draw_wordmark(d, 28, 11, 42, light=True)
    f = font(REG, 14)
    d.text((w - 28 - d.textlength(DATASET, font=f), (BAND - 16) // 2), DATASET, font=f, fill=MUTED)
    # footer
    d.line([(28, h - 26), (w - 28, h - 26)], fill=LINE, width=1)
    f = font(REG, 12)
    d.text((28, h - 21), FOOTER, font=f, fill=FOOT)
    page_tag = f"{w} × {h}"
    d.text((w - 28 - d.textlength(page_tag, font=f), h - 21), page_tag, font=f, fill=FOOT)
    return img


def logo(light: bool) -> Image.Image:
    img = Image.new("RGBA", (520, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    right = draw_wordmark(d, 12, 20, 80, light=light)
    return img.crop((0, 0, right + 16, 120))


def main() -> None:
    for w, h in ((1600, 900), (1600, 1200), (1600, 1600), (1600, 2000)):
        background(w, h).save(OUT / f"bg_{w}x{h}.png", optimize=True)
    logo(light=True).save(OUT / "logo_rota.png")
    logo(light=False).save(OUT / "logo_rota_dark.png")
    print("OK:", ", ".join(p.name for p in sorted(OUT.glob("*.png"))))


if __name__ == "__main__":
    main()
