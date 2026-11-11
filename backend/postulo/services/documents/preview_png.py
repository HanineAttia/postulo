"""PNG images of a PDF, for the visual review in the workshop (docs/SPEC.md section 16.1).

pypdfium2 renders each page to a raw RGB bitmap; a small PNG encoder (zlib and
struct from the standard library) writes it, so no image library is needed and
both rendering engines (Typst and HTML) get the same preview.
"""

from __future__ import annotations

import struct
import zlib

import pypdfium2 as pdfium

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def encode_png(rgb: bytes, width: int, height: int, stride: int) -> bytes:
    """Encode 8-bit RGB rows (`stride` bytes each, possibly padded) as a PNG file."""
    row = width * 3
    raw = b"".join(b"\x00" + rgb[y * stride : y * stride + row] for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB, no interlace
    return (
        PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 6))
        + _chunk(b"IEND", b"")
    )


def pdf_to_png_pages(pdf: bytes, *, scale: float = 1.5) -> list[bytes]:
    """One PNG per page. `scale` 1.5 is 108 dpi: readable on screen, a few hundred kB."""
    document = pdfium.PdfDocument(pdf)
    images: list[bytes] = []
    try:
        for index in range(len(document)):
            page = document[index]
            # rev_byteorder: RGB instead of pdfium's native BGR.
            bitmap = page.render(scale=scale, rev_byteorder=True)
            if bitmap.n_channels != 3:  # pragma: no cover - default format is 3 channels
                raise ValueError(f"Unexpected bitmap mode {bitmap.mode}")
            images.append(
                encode_png(bytes(bitmap.buffer), bitmap.width, bitmap.height, bitmap.stride)
            )
            bitmap.close()
            page.close()
    finally:
        document.close()
    return images
