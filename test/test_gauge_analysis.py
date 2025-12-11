#!/usr/bin/env python3
"""
Test different image processing and prompts for oil gauge analysis.
Uses a saved snapshot to avoid repeatedly calling the camera/API.
"""

import base64
import os
from PIL import Image

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-sonnet-4-5"


def process_test_image(image_path, degrees, output_path, flip_horizontal=False):
    """Process an image: flip and/or rotate, then save it."""
    img = Image.open(image_path)

    # Convert RGBA to RGB if saving as JPEG
    if output_path.lower().endswith(".jpg") or output_path.lower().endswith(".jpeg"):
        if img.mode == "RGBA":
            # Create a white background
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(
                img, mask=img.split()[3] if len(img.split()) == 4 else None
            )
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

    # Flip horizontally if needed (to fix mirrored/reversed text)
    if flip_horizontal:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

    # Rotate
    if degrees != 0:
        img = img.rotate(degrees, expand=True)

    img.save(output_path)

    flip_msg = " (flipped horizontally)" if flip_horizontal else ""
    print(f"✓ Processed image: rotated {degrees}°{flip_msg} and saved to {output_path}")
    return output_path


def analyze_image(image_path, prompt=None):
    """Send image to Claude for analysis."""
    if not ANTHROPIC_API_KEY:
        print("❌ Missing ANTHROPIC_API_KEY")
        return None

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = f.read()

    base64_image = base64.b64encode(image_data).decode("utf-8")

    # Determine media type
    if image_path.lower().endswith(".png"):
        media_type = "image/png"
    else:
        media_type = "image/jpeg"

    # Default prompt if none provided
    if not prompt:
        prompt = """This is a vertical oil tank float gauge with text markings for EMPTY (bottom), 1/4, 1/2, 3/4, and FULL (top). 

CRITICAL: The float indicator is a THICK/WIDE dark band or section - significantly thicker than the thin marking lines. Look carefully at the ENTIRE vertical gauge from bottom to top.

When the tank is FULL (100%):
- The thick float band will be at the very TOP of the gauge, near or at the "FULL" marking
- Don't be distracted by shadows, residue, or stains lower on the gauge
- The float physically rises to the top when full

When the tank is lower:
- Between 3/4 and FULL = 75-100%
- At 3/4 mark = ~75%
- Between 1/2 and 3/4 = 50-75%
- At 1/2 mark = ~50%
- Between 1/4 and 1/2 = 25-50%
- At 1/4 mark = ~25%
- Near EMPTY = 0-10%

SCAN THE ENTIRE GAUGE from top to bottom. The HIGHEST thick dark band is the float position.

Provide your response as:
Percentage: X%
Position: [location of the THICK float section]
Confidence: [High/Medium/Low]
Notes: [brief observations if helpful]

Note: Ignore the white cylindrical object (power supply) and thin reference lines."""

    # Create client and send request
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    message_list = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_image,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }
    ]

    try:
        print(f"🤖 Analyzing {image_path}...")
        response = client.messages.create(
            model=MODEL_NAME, max_tokens=2048, messages=message_list
        )

        result = response.content[0].text
        print("✓ Analysis complete\n")
        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    import sys
    import os

    # Detect available snapshots
    available_images = []
    for img in [
        "oil.png",
        "oil_snapshot_20251210_193037.jpg",
        "oil_camera_snapshot.jpg",
    ]:
        if os.path.exists(img):
            available_images.append(img)

    if not available_images:
        print("❌ No snapshot images found!")
        return

    print("=" * 80)
    print("Oil Gauge Analysis Tester")
    print("=" * 80)
    print("\nAvailable images:")
    for i, img in enumerate(available_images, 1):
        print(f"  {i}. {img}")

    img_choice = input(f"\nSelect image (1-{len(available_images)}): ").strip()
    try:
        snapshot = available_images[int(img_choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice, using first image")
        snapshot = available_images[0]

    print(f"\nUsing snapshot: {snapshot}")
    print("\nOptions:")
    print("  1. Test with original image (no rotation)")
    print("  2. Test with FLIP + 55° rotation (recommended - fixes mirrored text)")
    print("  3. Test with image rotated 55° clockwise (no flip)")
    print("  4. Test with custom rotation and flip")
    print("  5. Test with custom prompt (no rotation)")
    print("  6. Exit")

    choice = input("\nSelect option (1-6): ").strip()

    if choice == "1":
        print("\n--- Testing with original image ---")
        result = analyze_image(snapshot)
        if result:
            print("\n" + "=" * 80)
            print("RESULT:")
            print(result)
            print("=" * 80)

    elif choice == "2":
        print("\n--- Flipping horizontally and rotating 55° counterclockwise ---")
        processed = process_test_image(
            snapshot, 55, "oil_flipped_rotated_55.png", flip_horizontal=True
        )
        result = analyze_image(processed)
        if result:
            print("\n" + "=" * 80)
            print("RESULT:")
            print(result)
            print("=" * 80)

    elif choice == "3":
        print("\n--- Rotating image 55° clockwise (no flip) ---")
        processed = process_test_image(
            snapshot, -55, "oil_rotated_55.png", flip_horizontal=False
        )
        result = analyze_image(processed)
        if result:
            print("\n" + "=" * 80)
            print("RESULT:")
            print(result)
            print("=" * 80)

    elif choice == "4":
        degrees = int(input("Enter rotation degrees (negative for clockwise): "))
        flip = input("Flip horizontally? (y/n): ").strip().lower() == "y"
        processed = process_test_image(
            snapshot, degrees, f"oil_processed_{abs(degrees)}.png", flip_horizontal=flip
        )
        result = analyze_image(processed)
        if result:
            print("\n" + "=" * 80)
            print("RESULT:")
            print(result)
            print("=" * 80)

    elif choice == "5":
        print("\nEnter custom prompt (or press Enter for default):")
        custom_prompt = input("> ").strip()
        if not custom_prompt:
            custom_prompt = None
        result = analyze_image(snapshot, custom_prompt)
        if result:
            print("\n" + "=" * 80)
            print("RESULT:")
            print(result)
            print("=" * 80)

    elif choice == "6":
        print("Exiting...")
        return

    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
