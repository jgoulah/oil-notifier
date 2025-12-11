#!/usr/bin/env python3
"""
Quick script to grab latest snapshot, process it, and save what Claude sees.
"""

from io import BytesIO
from PIL import Image
from pathlib import Path

# Find most recent snapshot
images_dir = Path("images")
snapshots = sorted(
    images_dir.glob("oil_snapshot_*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True
)

if not snapshots:
    print("No snapshots found!")
    exit(1)

latest = snapshots[0]
print(f"Processing: {latest}")

# Read image
with open(latest, "rb") as f:
    image_data = f.read()

img = Image.open(BytesIO(image_data))

# Convert RGBA to RGB if needed
if img.mode == "RGBA":
    background = Image.new("RGB", img.size, (255, 255, 255))
    background.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
    img = background
elif img.mode != "RGB":
    img = img.convert("RGB")

# NO flip (camera now outputs correct orientation)
# Try both rotation directions to see which is correct

# Clockwise
img_cw = img.rotate(-55, expand=True)
img_cw.save("../images/rotated_clockwise.jpg", quality=95)
print(f"✓ Saved clockwise rotation (-55°) to ../images/rotated_clockwise.jpg")

# Counterclockwise
img_ccw = img.rotate(55, expand=True)
img_ccw.save("../images/rotated_counterclockwise.jpg", quality=95)
print(
    f"✓ Saved counterclockwise rotation (+55°) to ../images/rotated_counterclockwise.jpg"
)

print("\nCheck which rotation looks correct, then we'll use that one")

print("\nNext steps:")
print("1. Open ../images/rotated_clockwise.jpg and ../images/rotated_counterclockwise.jpg")
print("2. See which one looks correct (gauge should be upright)")
print("3. Let me know which direction is correct and we'll update the code")
