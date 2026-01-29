#!/usr/bin/env python3
"""
Check oil level by grabbing a snapshot from UniFi Protect camera
and analyzing it with Claude.
"""

import argparse
import base64
import csv
import os
import re
import smtplib
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from pathlib import Path

import requests
from anthropic import Anthropic
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# Configuration
UNIFI_HOST = os.getenv("UNIFI_HOST")
UNIFI_API_KEY = os.getenv("UNIFI_API_KEY")
CAMERA_ID = os.getenv("CAMERA_ID")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-sonnet-4-5"

# Alert configuration
ALERT_THRESHOLD = 25  # Alert when oil level drops below this percentage
ALERT_EMAIL = "jgoulah@gmail.com"
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "jgoulah@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Check oil level from camera")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory for images and log file (default: ./images and ./oil_level_log.csv)",
    )
    return parser.parse_args()

_args = parse_args()

# Paths - use --data-dir if provided, otherwise local paths
if _args.data_dir:
    DATA_DIR = Path(_args.data_dir)
    IMAGES_DIR = DATA_DIR / "images"
    LOG_FILE = DATA_DIR / "oil_level_log.csv"
else:
    IMAGES_DIR = Path(__file__).parent / "images"
    LOG_FILE = Path(__file__).parent / "oil_level_log.csv"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Disable SSL warnings for local UniFi
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_camera_snapshot():
    """Grab a snapshot from the UniFi Protect camera."""
    print("📷 Fetching camera snapshot...")

    if not all([UNIFI_HOST, UNIFI_API_KEY, CAMERA_ID]):
        print("❌ Missing UniFi configuration")
        print(f"   UNIFI_HOST: {'set' if UNIFI_HOST else 'MISSING'}")
        print(f"   UNIFI_API_KEY: {'set' if UNIFI_API_KEY else 'MISSING'}")
        print(f"   CAMERA_ID: {'set' if CAMERA_ID else 'MISSING'}")
        return None

    snapshot_url = f"https://{UNIFI_HOST}/proxy/protect/integration/v1/cameras/{CAMERA_ID}/snapshot"
    print(f"   URL: {snapshot_url}")

    headers = {"X-API-KEY": UNIFI_API_KEY, "Accept": "*/*"}

    try:
        response = requests.get(snapshot_url, headers=headers, verify=False, timeout=10)

        if response.status_code != 200:
            print(f"❌ Failed to get snapshot: {response.status_code}")
            print(f"   Response headers: {dict(response.headers)}")
            try:
                print(f"   Response body: {response.text[:500]}")
            except:
                print(f"   Response body: (could not decode)")
            return None

        print("✓ Snapshot retrieved successfully")
        return response.content

    except Exception as e:
        print(f"❌ Error fetching snapshot: {e}")
        import traceback
        traceback.print_exc()
        return None


def reduce_glare(img):
    """Reduce glare/reflections in the image, especially in the upper portion."""
    import numpy as np

    # Convert to numpy array
    img_array = np.array(img, dtype=np.float32)

    # Identify very bright pixels (potential glare) - threshold at 220 out of 255
    bright_mask = np.mean(img_array, axis=2) > 220

    # Reduce brightness of glare pixels
    glare_reduction = 0.7  # Reduce bright pixels to 70% of original
    for c in range(3):
        img_array[:, :, c] = np.where(
            bright_mask, img_array[:, :, c] * glare_reduction, img_array[:, :, c]
        )

    # Apply gradient darkening to top 40% of image (where reflections tend to occur)
    height = img_array.shape[0]
    top_portion = int(height * 0.4)

    for y in range(top_portion):
        # Gradual darkening: more at top, less toward middle
        darken_factor = 0.85 + (0.15 * y / top_portion)  # 0.85 at top, 1.0 at 40%
        img_array[y, :, :] *= darken_factor

    # Clip values to valid range
    img_array = np.clip(img_array, 0, 255).astype(np.uint8)

    return Image.fromarray(img_array)


def process_image(
    image_data, flip_horizontal=False, rotate_degrees=0, crop_box=None, enhance=True, reduce_glare_enabled=True
):
    """Process image: flip, rotate, crop, reduce glare, and enhance as needed."""
    from PIL import ImageEnhance

    # Load image from bytes
    img = Image.open(BytesIO(image_data))

    # Convert RGBA to RGB if needed
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Flip horizontally (mirror) if needed - this fixes reversed text
    if flip_horizontal:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

    # Rotate the image
    if rotate_degrees != 0:
        img = img.rotate(rotate_degrees, expand=True)

    # Crop if crop_box provided (left, upper, right, lower)
    if crop_box:
        img = img.crop(crop_box)

    # Reduce glare/reflections (especially important for IR camera images)
    if reduce_glare_enabled:
        img = reduce_glare(img)

    # Enhance brightness and contrast to make the gauge easier to read
    if enhance:
        # Increase brightness slightly
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.3)  # 30% brighter

        # Increase contrast to make the float more distinct
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.4)  # 40% more contrast

        # Increase sharpness to make markings clearer
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)  # 50% sharper

    # Convert back to bytes
    output = BytesIO()
    img.save(output, format="JPEG", quality=95)
    return output.getvalue()


def parse_percentage(result_text):
    """Extract percentage from Claude's response. Returns upper end of range if given."""
    # Look for patterns like "30-35%" or "Percentage: 35%" or just "35%"
    patterns = [
        r"Percentage:\s*(\d+)(?:-(\d+))?%",  # "Percentage: 30-35%" or "Percentage: 35%"
        r"(\d+)(?:-(\d+))%",  # "30-35%" or "35%"
    ]

    for pattern in patterns:
        match = re.search(pattern, result_text)
        if match:
            # If range given (e.g., 30-35), use upper end
            if match.group(2):
                return int(match.group(2))
            # Otherwise use the single number
            return int(match.group(1))

    return None


def log_reading(percentage, raw_result, snapshot_path):
    """Log oil level reading to CSV file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create CSV with header if it doesn't exist
    file_exists = LOG_FILE.exists()

    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Percentage", "Snapshot", "Raw Result"])
        writer.writerow(
            [timestamp, percentage, snapshot_path, raw_result.replace("\n", " ")]
        )

    print(f"📝 Logged reading to {LOG_FILE}")


def send_alert_email(percentage, snapshot_path, is_warning=False):
    """Send email with oil level status. Warning style when below threshold."""
    if is_warning:
        subject = f"⚠️ LOW OIL WARNING: {percentage}% Remaining ⚠️"
        status_text = "LOW - ACTION REQUIRED"
        status_color = "#dc3545"
        header_bg = "#dc3545"
        message = "<strong>Your oil tank is running low! Please schedule an oil delivery soon.</strong>"
        banner = """
<div style="background-color: #dc3545; color: white; padding: 15px; text-align: center; font-size: 18px; font-weight: bold;">
⚠️ LOW OIL WARNING - ACTION REQUIRED ⚠️
</div>
"""
    else:
        subject = f"📊 Oil Level Status: {percentage}%"
        status_text = "OK"
        status_color = "#28a745"
        header_bg = "#007bff"
        message = "Your oil level is within normal range."
        banner = ""

    # HTML body with inline image
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
{banner}
<div style="padding: 20px;">
<h2 style="color: {header_bg};">Oil Level {'Alert' if is_warning else 'Report'}</h2>
<p>{message}</p>

<table style="border-collapse: collapse; margin: 20px 0;">
<tr>
    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Current Level:</strong></td>
    <td style="padding: 10px; border: 1px solid #ddd; font-size: 18px; font-weight: bold; color: {status_color};">{percentage}%</td>
</tr>
<tr>
    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Status:</strong></td>
    <td style="padding: 10px; border: 1px solid #ddd; color: {status_color}; font-weight: bold;">{status_text}</td>
</tr>
<tr>
    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Alert Threshold:</strong></td>
    <td style="padding: 10px; border: 1px solid #ddd;">{ALERT_THRESHOLD}%</td>
</tr>
<tr>
    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Time:</strong></td>
    <td style="padding: 10px; border: 1px solid #ddd;">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
</tr>
</table>

<p><strong>Gauge Reading:</strong></p>
<img src="cid:gauge_image" style="max-width: 600px; border: 2px solid #ccc;">

<hr style="margin-top: 30px;">
<p style="font-size: 12px; color: #666;">This is an automated message from your oil level monitoring system.</p>
</div>
</body>
</html>
"""

    # Plain text alternative
    if is_warning:
        text_body = f"""
****************************************
⚠️  LOW OIL WARNING - ACTION REQUIRED  ⚠️
****************************************

Your oil tank is running low!

Current Level: {percentage}%
Status: LOW - ACTION REQUIRED
Alert Threshold: {ALERT_THRESHOLD}%
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Please schedule an oil delivery soon.

---
This is an automated message from your oil level monitoring system.
"""
    else:
        text_body = f"""
Oil Level Status Report
=======================

Your oil level is within normal range.

Current Level: {percentage}%
Status: OK
Alert Threshold: {ALERT_THRESHOLD}%
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---
This is an automated message from your oil level monitoring system.
"""

    try:
        # Create the root message
        msg = MIMEMultipart("related")
        msg["From"] = f"Oil Monitor <{SMTP_USERNAME}>"
        msg["To"] = ALERT_EMAIL
        msg["Subject"] = subject

        # Create alternative part for text/html
        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)

        # Attach text and HTML versions to the alternative part
        msg_alternative.attach(MIMEText(text_body, "plain"))
        msg_alternative.attach(MIMEText(html_body, "html"))

        # Attach the image to the root message
        if os.path.exists(snapshot_path):
            with open(snapshot_path, "rb") as f:
                img_data = f.read()

            image = MIMEImage(img_data)
            image.add_header("Content-ID", "<gauge_image>")
            image.add_header(
                "Content-Disposition",
                "inline",
                filename=os.path.basename(snapshot_path),
            )
            msg.attach(image)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Enable TLS encryption
            if SMTP_USERNAME and SMTP_PASSWORD:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        email_type = "warning" if is_warning else "status"
        print(f"📧 {email_type.capitalize()} email sent to {ALERT_EMAIL}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def analyze_oil_gauge(image_data):
    """Send image to Claude for analysis."""
    print("🤖 Analyzing oil gauge with Claude...")

    if not ANTHROPIC_API_KEY:
        print("❌ Missing ANTHROPIC_API_KEY")
        return None, None, None

    # Process image: rotate and crop to isolate just the gauge
    # Note: Camera now outputs correct orientation, no flip needed
    # Rotate counterclockwise (+55)
    # Don't enhance - it adds noise
    # Reduce glare to help distinguish float from reflections
    # Crop coordinates (left, top, right, bottom) on the rotated image to focus on gauge only
    print("🔄 Processing image (rotating, cropping, and reducing glare)...")
    crop_box = (700, 650, 1300, 1600)  # Updated crop for new camera orientation
    processed_image_data = process_image(
        image_data,
        flip_horizontal=False,  # Camera is now set to correct orientation
        rotate_degrees=55,  # Counterclockwise rotation
        crop_box=crop_box,
        enhance=False,
        reduce_glare_enabled=True,  # Reduce reflections that confuse float detection
    )

    # Save processed image for email/debugging (resize by 50% for email)
    processed_filename = (
        IMAGES_DIR / f"processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    )

    # Resize for email (50% smaller)
    img_for_email = Image.open(BytesIO(processed_image_data))
    new_size = (img_for_email.width // 2, img_for_email.height // 2)
    img_for_email = img_for_email.resize(new_size, Image.Resampling.LANCZOS)

    # Save resized image
    img_for_email.save(processed_filename, format="JPEG", quality=90)

    # Convert image to base64 (use original size for Claude analysis)
    base64_image = base64.b64encode(processed_image_data).decode("utf-8")

    # Create Anthropic client
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Prepare message with improved prompt
    message_list = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64_image,
                    },
                },
                {
                    "type": "text",
                    "text": """This is a vertical oil tank float gauge. Your task is to determine the oil level percentage.

GAUGE STRUCTURE:
- Clear tube with labeled markers: FULL (top), 3/4, 1/2, 1/4, EMPTY (bottom)
- A FLOAT (thick disc, ~4-5mm) moves up/down inside the tube
- The float appears as a THICK HORIZONTAL BAND when viewed from the side

CRITICAL - IDENTIFYING THE REAL FLOAT VS REFLECTIONS:
⚠️ This infrared camera image has BRIGHT REFLECTIONS that look like horizontal bands, especially NEAR THE TOP of the gauge (between 3/4 and FULL).
⚠️ DO NOT mistake these reflections for the float!

How to distinguish the REAL FLOAT from reflections:
1. The real float is a SOLID, UNIFORM thickness horizontal band (~4-5mm thick)
2. The real float has CLEAR DEFINED EDGES (top and bottom edges are sharp)
3. Reflections appear as BRIGHT GLARE, often with fuzzy/uneven edges or varying brightness
4. Reflections often appear near the TOP of the gauge due to lighting angle
5. The float is typically DARKER or more SOLID than bright glare spots

STEP 1 - Scan the ENTIRE gauge from bottom to top:
Look at the full length of the tube. Identify ALL horizontal bands you see, noting their position and characteristics.

STEP 2 - Eliminate reflections:
Any bright, glary, or fuzzy horizontal features near the top (FULL to 3/4 region) are likely reflections. The real float will be a solid, well-defined band.

STEP 3 - Find the real float:
The float is the solid, uniform-thickness horizontal band with clear edges. It may be anywhere from EMPTY to FULL. Do NOT assume it's near the top just because you see brightness there.

STEP 4 - Calculate percentage:
- EXACTLY at EMPTY marker = 0%
- EXACTLY at 1/4 marker = 25%
- EXACTLY at 1/2 marker = 50%
- EXACTLY at 3/4 marker = 75%
- EXACTLY at FULL marker = 100%

For positions between markers, interpolate linearly.

RESPOND WITH:
Observations: [List ALL horizontal bands/features you see, from bottom to top, noting which appear to be reflections vs the real float]
Float position: [describe exactly where the REAL float is, after eliminating reflections]
Calculation: [show your work]
Percentage: X%
Confidence: [High/Medium/Low]""",
                },
            ],
        }
    ]

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=2048,
            temperature=0,  # Use deterministic responses for consistency
            messages=message_list,
        )

        result = response.content[0].text
        print("✓ Analysis complete")

        # Parse percentage from result
        percentage = parse_percentage(result)

        return result, percentage, str(processed_filename)

    except Exception as e:
        print(f"❌ Error analyzing image: {e}")
        return None, None, None


def main():
    """Main function to check oil level."""
    print("=" * 80)
    print("Oil Level Monitor")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Step 1: Get snapshot
    image_data = get_camera_snapshot()
    if not image_data:
        print("\n❌ Failed to get camera snapshot")
        return

    # Save snapshot to images directory
    snapshot_filename = (
        IMAGES_DIR / f"oil_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    )
    with open(snapshot_filename, "wb") as f:
        f.write(image_data)
    print(f"💾 Snapshot saved to {snapshot_filename}")

    # Step 2: Analyze with Claude
    result, percentage, processed_path = analyze_oil_gauge(image_data)
    if not result:
        print("\n❌ Failed to analyze oil gauge")
        return

    # Display result
    print("\n" + "=" * 80)
    print("📊 RESULT:")
    print(result)
    print("=" * 80)

    if percentage is not None:
        print(f"\n📊 Oil Level: {percentage}%")

        # Log the reading
        log_reading(percentage, result, str(snapshot_filename))

        # Check if alert needed
        is_warning = percentage <= ALERT_THRESHOLD
        if is_warning:
            print(
                f"\n⚠️  WARNING: Oil level ({percentage}%) is at or below threshold ({ALERT_THRESHOLD}%)"
            )
        else:
            print(f"\n✓ Oil level OK ({percentage}% > {ALERT_THRESHOLD}% threshold)")

        # Always send email, with warning flag when below threshold
        send_alert_email(percentage, processed_path, is_warning=is_warning)
    else:
        print("\n⚠️  Could not parse percentage from result")


if __name__ == "__main__":
    main()
