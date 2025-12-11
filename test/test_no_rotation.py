#!/usr/bin/env python3
"""
Test with no rotation - just crop the raw image from camera
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

print(f"Image size: {img.size[0]} x {img.size[1]}")

# NO rotation - save as-is
img.save("../images/no_rotation.jpg", quality=95)
print(f"✓ Saved image with NO rotation to ../images/no_rotation.jpg")
print(
    "\nOpen this image and see if the gauge is upright enough to use without rotation"
)
print("If yes, we can skip rotation and just crop!")
