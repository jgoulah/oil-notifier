#!/usr/bin/env python3
"""
Process an image the same way we send it to Claude, so we can see what it sees.
"""

from io import BytesIO
from PIL import Image, ImageEnhance


def process_image(image_path, output_path):
    """Process image exactly like we do for Claude."""
    # Read image
    with open(image_path, "rb") as f:
        image_data = f.read()

    # Load image from bytes
    img = Image.open(BytesIO(image_data))

    # Convert RGBA to RGB if needed
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Flip horizontally (mirror) to fix reversed text
    img = img.transpose(Image.FLIP_LEFT_RIGHT)

    # Rotate 55 degrees counterclockwise
    img = img.rotate(55, expand=True)

    # No enhancement - it adds noise

    # Save
    img.save(output_path, format="JPEG", quality=95)
    print(f"✓ Processed image saved to {output_path}")
    print("This is what Claude will see when analyzing the gauge.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python3 process_and_save.py <input_image> <output_image>")
        print(
            "Example: python3 process_and_save.py oil_snapshot_20251210_193037.jpg processed_for_claude.jpg"
        )
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    process_image(input_path, output_path)
