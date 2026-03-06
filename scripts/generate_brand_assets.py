"""Generate all brand image variants from the source logo."""

from pathlib import Path

import numpy as np
from PIL import Image

STATIC = Path(__file__).resolve().parent.parent / "static"
SOURCE = STATIC / "logo-source.png"

OG_BG_COLOR = (17, 15, 12)  # --bg2: #110f0c
BLACK_THRESHOLD = 30        # pixels with R,G,B all below this become transparent


def remove_black_background(img: Image.Image) -> Image.Image:
    """Replace black/near-black pixels with transparency using smooth alpha blending."""
    rgba = img.convert("RGBA")
    data = np.array(rgba, dtype=np.float64)
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]

    brightness = np.maximum(r, np.maximum(g, b))

    t = BLACK_THRESHOLD
    fade = 12  # transition band width for smooth edges
    new_alpha = np.clip((brightness - t) / fade, 0.0, 1.0) * a
    data[:, :, 3] = new_alpha

    return Image.fromarray(data.astype(np.uint8))


def autocrop(img: Image.Image, padding: int = 4) -> Image.Image:
    """Crop to the non-transparent bounding box with optional padding."""
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        return img
    left, upper, right, lower = bbox
    left = max(0, left - padding)
    upper = max(0, upper - padding)
    right = min(img.width, right + padding)
    lower = min(img.height, lower + padding)
    return img.crop((left, upper, right, lower))


def fit_square(img: Image.Image, size: int) -> Image.Image:
    """Resize image to fit inside a square, preserving aspect ratio, with transparent padding."""
    thumb = img.copy()
    thumb.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - thumb.width) // 2
    y = (size - thumb.height) // 2
    canvas.paste(thumb, (x, y), thumb)
    return canvas


def make_og_image(img: Image.Image, width: int = 1200, height: int = 630) -> Image.Image:
    """Create OG image: logo centered on branded dark background."""
    canvas = Image.new("RGBA", (width, height), (*OG_BG_COLOR, 255))

    logo_h = int(height * 0.70)
    ratio = logo_h / img.height
    logo_w = int(img.width * ratio)
    resized = img.resize((logo_w, logo_h), Image.LANCZOS)

    x = (width - logo_w) // 2
    y = (height - logo_h) // 2
    canvas.paste(resized, (x, y), resized if resized.mode == "RGBA" else None)
    return canvas.convert("RGB")


def main() -> None:
    if not SOURCE.exists():
        print(f"Source logo not found at {SOURCE}")
        return

    raw = Image.open(SOURCE)
    print(f"Source image: {raw.width}x{raw.height}, mode={raw.mode}")

    src = remove_black_background(raw)
    src = autocrop(src)
    print(f"After background removal & crop: {src.width}x{src.height}")

    variants = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "apple-touch-icon.png": 180,
        "android-chrome-192x192.png": 192,
        "android-chrome-512x512.png": 512,
    }

    for name, size in variants.items():
        out = fit_square(src, size)
        out.save(STATIC / name, "PNG")
        print(f"  {name} ({size}x{size})")

    logo_width = 300
    ratio = logo_width / src.width
    logo_height = int(src.height * ratio)
    logo = src.resize((logo_width, logo_height), Image.LANCZOS)
    logo.save(STATIC / "logo.png", "PNG")
    print(f"  logo.png ({logo_width}x{logo_height})")

    ico_16 = fit_square(src, 16)
    ico_32 = fit_square(src, 32)
    ico_32.save(STATIC / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32)])
    print("  favicon.ico (16+32)")

    og = make_og_image(src)
    og.save(STATIC / "og-image.png", "PNG")
    print(f"  og-image.png ({og.width}x{og.height})")

    print("\nDone! All brand assets saved to static/")


if __name__ == "__main__":
    main()
