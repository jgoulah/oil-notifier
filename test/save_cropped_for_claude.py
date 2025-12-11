#!/usr/bin/env python3
"""
Save the exact cropped image that Claude will analyze.
This helps debug what Claude is seeing.
"""

from io import BytesIO
from PIL import Image, ImageEnhance


def process_and_save(image_path, output_path):
    """Process and save the exact image Claude will see."""
    # Read image
    with open(image_path, "rb") as f:
        image_data = f.read()

    img = Image.open(BytesIO(image_data))

    # Convert RGBA to RGB if needed
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Flip horizontally
    img = img.transpose(Image.FLIP_LEFT_RIGHT)

    # Rotate 55 degrees counterclockwise
    img = img.rotate(55, expand=True)

    # Crop to gauge area (same coordinates as check_oil_level.py)
    crop_box = (975, 875, 1241, 1400)
    img = img.crop(crop_box)

    # Save
    img.save(output_path, format="JPEG", quality=95)
    print(f"✓ Saved cropped image that Claude will see to: {output_path}")
    print(f"  Image size: {img.size[0]} x {img.size[1]}")
    print(f"  This is exactly what gets sent to Claude for analysis")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python3 save_cropped_for_claude.py <input_image> <output_image>")
        print(
            "Example: python3 save_cropped_for_claude.py oil_snapshot_20251210_193037.jpg claude_view.jpg"
        )
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    process_and_save(input_path, output_path)
