#!/usr/bin/env python3
"""
Test email alert functionality.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from check_oil_level import send_alert_email

if __name__ == "__main__":
    print("Testing email alert...")
    print("=" * 80)

    # Test with processed image
    test_percentage = 20

    # Find a recent processed image (or snapshot as fallback)
    import glob

    images_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images"
    )

    # Try to find a processed image first
    processed = glob.glob(os.path.join(images_dir, "processed_*.jpg"))
    if processed:
        test_snapshot = max(processed, key=os.path.getmtime)
        print(f"Using processed image: {test_snapshot}")
    else:
        # Fallback to snapshot
        snapshots = glob.glob(os.path.join(images_dir, "oil_snapshot_*.jpg"))
        if snapshots:
            test_snapshot = max(snapshots, key=os.path.getmtime)
            print(f"Using snapshot (no processed images found): {test_snapshot}")
            print("Note: Run check_oil_level.py first to generate processed images")
        else:
            print("No images found! Run check_oil_level.py first.")
            sys.exit(1)

    success = send_alert_email(test_percentage, test_snapshot)

    if success:
        print("\n✓ Email test successful!")
        print("Check your inbox at jgoulah@gmail.com")
    else:
        print("\n✗ Email test failed - check the error above")
