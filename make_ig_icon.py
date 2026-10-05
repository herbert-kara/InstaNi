#!/usr/bin/env python3
"""InstaNi launcher icon: Instagram's own geometry and glyph, one small change.

The mod replaced the *content* of ig_launcher_background/foreground while keeping
Instagram's file names, so there is no pristine Instagram artwork left in the APK
to reuse. We redraw it instead: identical gradient stops, identical camera glyph,
and exactly one change -- the gradient is mirrored corner-to-corner, so the yellow
sits at the bottom-right instead of the top-left. Instantly recognisable as
Instagram, visibly not Instagram.
"""
import os

from PIL import Image, ImageDraw

OUT = r"Z:\hermes\instapro\build\igicon"
DENSITIES = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
LEGACY_SIZES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
SS = 4  # supersampling factor for smooth edges

# Instagram's gradient, mirrored 180 degrees (the one change we make): the yellow
# ends up at the bottom-right instead of the top-left. Bilinear across four corners
# reproduces IG's colour distribution far better than a single diagonal ramp.
CORNERS_MIRRORED = {  # (x, y) in 0..1 -> RGB
    (0.0, 0.0): (0x96, 0x2F, 0xBF),   # top-left     purple   (IG: yellow)
    (1.0, 0.0): (0xD6, 0x29, 0x76),   # top-right    magenta  (IG: orange)
    (1.0, 1.0): (0xFE, 0xDA, 0x75),   # bottom-right yellow   (IG: blue)
    (0.0, 1.0): (0xFA, 0x7E, 0x1E),   # bottom-left  orange   (IG: purple)
}
CENTRE_BLUE = (0x4F, 0x5B, 0xD5)      # IG's blue heart, kept and softened
CENTRE_MIX = 0.78


def gradient(size):
    """Bilinear four-corner gradient, matching Instagram's colour spread."""
    im = Image.new("RGB", (size, size))
    px = im.load()
    c00, c10, c11, c01 = (CORNERS_MIRRORED[(0.0, 0.0)], CORNERS_MIRRORED[(1.0, 0.0)],
                          CORNERS_MIRRORED[(1.0, 1.0)], CORNERS_MIRRORED[(0.0, 1.0)])
    for y in range(size):
        fy = y / (size - 1)
        for x in range(size):
            fx = x / (size - 1)
            col = []
            for i in range(3):
                top = c00[i] + (c10[i] - c00[i]) * fx
                bot = c01[i] + (c11[i] - c01[i]) * fx
                base = top + (bot - top) * fy
                # pull the centre toward IG's signature blue
                w = CENTRE_MIX * max(0.0, 1.0 - 2 * abs(fx - 0.5)) * max(0.0, 1.0 - 2 * abs(fy - 0.5))
                col.append(int(round(base + (CENTRE_BLUE[i] - base) * w)))
            px[x, y] = tuple(col)
    return im


def glyph_layer(size):
    """Instagram's camera glyph, white, inside the 72/108 adaptive safe zone."""
    s = size * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = s / 108.0          # one adaptive-icon unit, in supersampled pixels
    stroke = int(round(7.2 * u))

    # camera body: rounded-square outline
    d.rounded_rectangle([int(29.5 * u), int(29.5 * u), int(78.5 * u), int(78.5 * u)],
                        radius=int(16.5 * u), outline=(255, 255, 255, 255), width=stroke)
    # lens ring
    r_out, r_in = 11.6 * u, 11.6 * u - stroke / 2
    d.ellipse([54 * u - r_out, 54 * u - r_out, 54 * u + r_out, 54 * u + r_out],
              outline=(255, 255, 255, 255), width=stroke)
    # the small dot, upper right
    r = 4.3 * u
    d.ellipse([69 * u - r, 40 * u - r, 69 * u + r, 40 * u + r], fill=(255, 255, 255, 255))
    return im.resize((size, size), Image.LANCZOS)


def legacy(size):
    """Pre-API-26 icon: the same artwork, rounded square, no transparent corners."""
    S = size * SS
    bg = gradient(S).convert("RGBA")
    fg = glyph_layer(S)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1],
                                           radius=int(S * 0.235), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(Image.alpha_composite(bg, fg), (0, 0), mask)
    return out.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    lines = []
    for dens in DENSITIES:
        gradient(DENSITIES[dens]).save(os.path.join(OUT, f"{dens}_bg.png"))
        glyph_layer(DENSITIES[dens]).save(os.path.join(OUT, f"{dens}_fg.png"))
        legacy(LEGACY_SIZES[dens]).save(os.path.join(OUT, f"{dens}_legacy.png"))
        lines += [f"res/mipmap-{dens}/ig_launcher_background.png={OUT}\\{dens}_bg.png",
                  f"res/mipmap-{dens}/ig_launcher_foreground.png={OUT}\\{dens}_fg.png",
                  f"res/mipmap-{dens}/icon.png={OUT}\\{dens}_legacy.png"]
    # previews for review
    legacy(432).resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "preview_instani.png"))
    print("wrote", len(lines), "icon files + preview to", OUT)
