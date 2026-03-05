#!/usr/bin/env python3
"""
Test the gauge analysis on a saved image file (not from camera).
Uses the same processing as check_oil_level.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# check_oil_level.py calls parse_args() at import time — mask our args first
_real_argv = sys.argv[:]
sys.argv = sys.argv[:1]
from check_oil_level import analyze_oil_gauge
sys.argv = _real_argv

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test gauge analysis on a saved image")
    parser.add_argument("image_path", help="Path to image file")
    parser.add_argument(
        "--skip-processing",
        action="store_true",
        help="Skip rotation/crop/glare-reduction (use when image is already a processed gauge shot)",
    )
    args = parser.parse_args()

    print(f"Testing gauge analysis on: {args.image_path}")
    if args.skip_processing:
        print("Mode: pre-processed image (no rotation/crop/glare reduction)")
    else:
        print("Mode: raw camera image (full pipeline)")
    print("=" * 80)

    with open(args.image_path, "rb") as f:
        image_data = f.read()

    result, percentage, processed_path = analyze_oil_gauge(image_data, skip_processing=args.skip_processing)

    if result:
        print("\n" + "=" * 80)
        print("RESULT:")
        print(result)
        print("=" * 80)

        if percentage is not None:
            print(f"\n📊 Parsed Oil Level: {percentage}%")
        else:
            print("\n⚠️  Could not parse percentage from result")

        print(f"\n🖼️  Processed image saved to: {processed_path}")
    else:
        print("\nFailed to analyze image")
