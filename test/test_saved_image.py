#!/usr/bin/env python3
"""
Test the gauge analysis on a saved image file (not from camera).
Uses the same processing as check_oil_level.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import sys; import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); from check_oil_level import analyze_oil_gauge

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 test_saved_image.py <image_path>")
        print("Example: python3 test_saved_image.py oil.png")
        sys.exit(1)

    image_path = sys.argv[1]

    print(f"Testing gauge analysis on: {image_path}")
    print("=" * 80)

    with open(image_path, "rb") as f:
        image_data = f.read()

    result, percentage = analyze_oil_gauge(image_data)

    if result:
        print("\n" + "=" * 80)
        print("RESULT:")
        print(result)
        print("=" * 80)

        if percentage is not None:
            print(f"\n📊 Parsed Oil Level: {percentage}%")
        else:
            print("\n⚠️  Could not parse percentage from result")
    else:
        print("\nFailed to analyze image")
