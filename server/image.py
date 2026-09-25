"""Image normalization to match the ingester's rasterization output.

Mirrors what the Sharp sidecar originally did: flatten alpha to white,
fit-contain into 256×256 with white letterboxing.
"""

from __future__ import annotations

import io

from PIL import Image


def normalize(data: bytes, size: int = 256) -> bytes:
    """Return a 256×256 white-background PNG suitable for jina-clip-v2."""
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.paste(img, mask=img.split()[3])
    rgb = bg.convert("RGB")
    rgb.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    canvas.paste(rgb, ((size - rgb.width) // 2, (size - rgb.height) // 2))
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
