#!/usr/bin/env python3
"""
Simple crop tool - just crops, no rotation or processing.
Use this on already-rotated images.
"""

import sys
from PIL import Image

if __name__ == "__main__":
    if len(sys.argv) not in [2, 6]:
        print("Usage: python3 simple_crop.py <image_path> [left top right bottom]")
        print(
            "Example: python3 simple_crop.py ../images/rotated_for_cropping.jpg 700 400 1000 1800"
        )
        sys.exit(1)

    image_path = sys.argv[1]

    # Load image
    img = Image.open(image_path)
    print(f"Image size: {img.size[0]} x {img.size[1]}")

    if len(sys.argv) == 6:
        # Crop coordinates provided
        left, top, right, bottom = [int(sys.argv[i]) for i in range(2, 6)]
        crop_box = (left, top, right, bottom)
    else:
        # Default center crop
        width, height = img.size
        crop_width = width // 4
        margin = (width - crop_width) // 2
        crop_box = (margin, 0, margin + crop_width, height)

    print(f"Crop box: {crop_box}")
    print(f"  Left: {crop_box[0]}, Top: {crop_box[1]}")
    print(f"  Right: {crop_box[2]}, Bottom: {crop_box[3]}")
    print(f"  Width: {crop_box[2] - crop_box[0]}, Height: {crop_box[3] - crop_box[1]}")

    # Validate
    if crop_box[0] >= crop_box[2] or crop_box[1] >= crop_box[3]:
        print("ERROR: Invalid crop box - right must be > left, bottom must be > top")
        sys.exit(1)

    if crop_box[2] > img.size[0] or crop_box[3] > img.size[1]:
        print(f"ERROR: Crop box exceeds image bounds ({img.size[0]} x {img.size[1]})")
        sys.exit(1)

    # Crop
    cropped = img.crop(crop_box)
    output_path = "../images/simple_crop_preview.jpg"
    cropped.save(output_path, quality=95)

    print(f"\n✓ Saved cropped image to {output_path}")
    print(f"  Cropped size: {cropped.size[0]} x {cropped.size[1]}")
    print(f"\nIf this looks good, use these coordinates in check_oil_level.py:")
    print(f"  crop_box = {crop_box}")
