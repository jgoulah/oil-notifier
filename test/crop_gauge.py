#!/usr/bin/env python3
"""
Interactive tool to crop the gauge from the image.
Shows the processed image and lets you specify crop coordinates.
"""

from io import BytesIO
from PIL import Image, ImageDraw


def process_image(image_path):
    """Process image the same way we do for analysis."""
    with open(image_path, "rb") as f:
        image_data = f.read()

    img = Image.open(BytesIO(image_data))

    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Flip and rotate
    img = img.transpose(Image.FLIP_LEFT_RIGHT)
    img = img.rotate(55, expand=True)

    return img


def get_crop_coordinates(img):
    """Interactive function to get crop coordinates."""
    width, height = img.size

    print(f"\nImage size after processing (flipped + rotated): {width} x {height}")
    print("\nWe need to define a crop box to isolate just the gauge.")
    print("\nCrop box format: (left, top, right, bottom)")
    print("  left:   pixels from LEFT edge (0 = far left, larger = move right)")
    print("  top:    pixels from TOP edge (0 = top, larger = move down)")
    print("  right:  pixels from LEFT edge (must be > left)")
    print("  bottom: pixels from TOP edge (must be > top)")
    print("\nThink of it like drawing a rectangle:")
    print("  left/top = upper-left corner of the rectangle")
    print("  right/bottom = lower-right corner of the rectangle")
    print("\nTo ADJUST the crop:")
    print("  - Tighten top: INCREASE the 'top' number (cuts off more from top)")
    print(
        "  - Tighten bottom: DECREASE the 'bottom' number (cuts off more from bottom)"
    )
    print("  - Tighten left: INCREASE the 'left' number")
    print("  - Tighten right: DECREASE the 'right' number")

    # Save the processed image for reference with grid overlay
    img_with_grid = img.copy()
    draw = ImageDraw.Draw(img_with_grid)

    # Draw center lines for reference
    draw.line([(width // 2, 0), (width // 2, height)], fill="red", width=2)
    draw.line([(0, height // 2), (width, height // 2)], fill="red", width=2)

    img_with_grid.save("processed_for_cropping.jpg", quality=95)
    print(
        f"\n✓ Saved 'processed_for_cropping.jpg' - open this to see what we're working with"
    )
    print("  (Red lines show center for reference)")

    print("\nEnter crop coordinates (or press Enter to try default center crop):")

    user_input = input("left top right bottom: ").strip()

    if not user_input:
        # Default: try to crop center vertical strip
        crop_width = width // 4  # Take center 1/4 of width
        margin = (width - crop_width) // 2
        crop_box = (margin, 0, margin + crop_width, height)
        print(f"Using default center crop: {crop_box}")
        print(
            f"  This crops from x={margin} to x={margin + crop_width}, y=0 to y={height}"
        )
    else:
        try:
            parts = user_input.split()
            crop_box = tuple(int(p) for p in parts)
            if len(crop_box) != 4:
                print("Error: Need 4 numbers")
                return None
            left, top, right, bottom = crop_box
            print(f"  This will crop from x={left} to x={right} (width={right - left})")
            print(f"                    y={top} to y={bottom} (height={bottom - top})")
        except ValueError:
            print("Error: Invalid numbers")
            return None

    return crop_box


def save_cropped_preview(img, crop_box, output_path):
    """Save a preview of the cropped image."""
    cropped = img.crop(crop_box)
    cropped.save(output_path, quality=95)
    print(f"\n✓ Saved cropped preview to '{output_path}'")
    print(f"Cropped size: {cropped.size[0]} x {cropped.size[1]}")
    return cropped


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 crop_gauge.py <image_path> [left top right bottom]")
        print("\nExamples:")
        print("  python3 crop_gauge.py oil.png")
        print("  python3 crop_gauge.py oil.png 750 250 1250 1250")
        sys.exit(1)

    image_path = sys.argv[1]

    print("=" * 80)
    print("Gauge Cropping Tool")
    print("=" * 80)

    print("\nProcessing image (flip + rotate)...")
    img = process_image(image_path)

    # If crop coordinates provided as arguments
    if len(sys.argv) == 6:
        try:
            crop_box = tuple(int(sys.argv[i]) for i in range(2, 6))
            print(f"Using provided crop box: {crop_box}")
        except ValueError:
            print("Error: Invalid crop coordinates")
            sys.exit(1)
    else:
        crop_box = get_crop_coordinates(img)
        if not crop_box:
            sys.exit(1)

    # Save cropped preview
    cropped = save_cropped_preview(img, crop_box, "gauge_cropped_preview.jpg")

    print("\n" + "=" * 80)
    print("Next steps:")
    print("1. Open 'gauge_cropped_preview.jpg' to see the cropped gauge")
    print("2. If it looks good, use these coordinates in the main script")
    print(f"3. Crop coordinates to use: {crop_box}")
    print("\nTo try different crop coordinates, run:")
    print(f"  python3 crop_gauge.py {image_path} left top right bottom")
    print("=" * 80)
