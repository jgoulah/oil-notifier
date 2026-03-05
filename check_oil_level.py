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

    # Identify very bright pixels (potential glare) - crush the glare blobs
    brightness = np.mean(img_array, axis=2)
    bright_mask = brightness > 210

    # Reduce brightness of glare pixels
    glare_reduction = 0.55
    for c in range(3):
        img_array[:, :, c] = np.where(
            bright_mask, img_array[:, :, c] * glare_reduction, img_array[:, :, c]
        )

    # Apply gradient darkening to top 30% of image only
    # Keep this limited so the float region (which can be anywhere) stays readable
    height = img_array.shape[0]
    top_portion = int(height * 0.30)

    for y in range(top_portion):
        # Moderate darkening: 0.70 at top, 1.0 at 30% mark
        darken_factor = 0.70 + (0.30 * y / top_portion)
        img_array[y, :, :] *= darken_factor

    # Clip values to valid range
    img_array = np.clip(img_array, 0, 255).astype(np.uint8)

    return Image.fromarray(img_array)


def process_image(
    image_data, flip_horizontal=False, rotate_degrees=0, crop_box=None, enhance=True, reduce_glare_enabled=True, equalize=True
):
    """Process image: flip, rotate, crop, reduce glare, and enhance as needed."""
    from PIL import ImageEnhance, ImageOps

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

    # Apply histogram equalization to spread the dynamic range and reveal
    # detail hidden in dark or bright regions (e.g. float inside glare zone)
    if equalize:
        img = ImageOps.equalize(img)

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
        r"\*{0,2}Percentage\*{0,2}:?\s*\*{0,2}\s*(\d+)(?:-(\d+))?%",  # "Percentage: 35%" or "**Percentage**: 35%"
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


def analyze_oil_gauge(image_data, skip_processing=False):
    """Send image to Claude for analysis.

    Args:
        image_data: Raw image bytes (camera snapshot or pre-processed image).
        skip_processing: If True, skip rotation/crop/glare-reduction and send the
                         image directly to Claude. Use when the image is already a
                         processed/cropped gauge shot (e.g. a saved processed_ file).
    """
    print("🤖 Analyzing oil gauge with Claude...")

    if not ANTHROPIC_API_KEY:
        print("❌ Missing ANTHROPIC_API_KEY")
        return None, None, None

    if skip_processing:
        print("⏭️  Skipping image processing (using image as-is)...")
        processed_image_data = image_data
    else:
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
            equalize=True,  # Spread dynamic range to reveal float detail in glare zones
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
                    "text": """This is a vertical oil tank float gauge captured by an infrared (IR) camera. Your task is to determine the oil level percentage.

GAUGE STRUCTURE:
- Clear tube with labeled markers: FULL (top), 3/4, 1/2, 1/4, EMPTY (bottom)
- A FLOAT (thick disc, ~4-5mm) moves up/down inside the tube
- The float appears as a THICK HORIZONTAL BAND when viewed from the side

KNOWN IR CAMERA ARTIFACTS:
⚠️ ARTIFACT 1 — BRIGHT VERTICAL CENTER STREAK: The IR camera creates a BRIGHT WHITE VERTICAL LINE running down the center of the gauge tube. This is NOT the float. It is a fixed optical artifact.
⚠️ ARTIFACT 2 — LARGE CENTRAL GLARE BLOB: The IR lighting creates a VERY LARGE bright/white region that can span 50%+ of the gauge height. The float disc is often EMBEDDED WITHIN this glare region in the center. The float is NOT visible as a dark band in the center when glare is heavy.

⚠️ ARTIFACT 3 — EXTERNAL MOUNTING HARDWARE: There are metal clamps/brackets that attach the gauge to the pipe, visible on the OUTSIDE of the glass tube. These create dark horizontal shadows at fixed positions (commonly near the bottom of the gauge). These are EXTERNAL and are NOT the float. The float is INSIDE the tube.

THE KEY TECHNIQUE — LOOK AT THE TUBE WALLS, NOT THE CENTER:
The float is a solid disc that spans the full width of the tube. Even when the center of the tube is completely obscured by IR glare, the EDGES of the float disc are visible where they intersect the LEFT and RIGHT walls of the tube. These appear as:
- A small, sharp horizontal dark notch or shadow on the LEFT wall of the tube
- A matching small, sharp horizontal dark notch or shadow on the RIGHT wall of the tube
- Both at the SAME vertical height — this is the float level

The float disc can be ANYWHERE in the gauge — at any percentage from 0-100. Do NOT assume it is in the lower half.

STEP 1 - Locate the text labels as anchors:
Find the vertical positions of: FULL (top), 3/4, 1/2, 1/4, EMPTY (bottom). These are your reference points.

STEP 2 - Assess the glare blob extent:
Note the TOP and BOTTOM edges of the large central glare blob. Record which gauge labels (FULL, 3/4, 1/2, 1/4) each boundary is nearest to.

CRITICAL RULE — LARGE GLARE SCENARIO: The float disc causes IR glare that extends both above and below its actual position. When the glare blob spans a large portion of the gauge (top edge near FULL, bottom edge at or above 1/2), the float is located at approximately the MIDPOINT (center) of the glare blob — halfway between its top and bottom boundaries. For example, if the glare extends from FULL to 1/2, the center is 75% = 3/4 level.

STEP 3 - Examine the LEFT and RIGHT tube walls:
Scan BOTH side walls for matching horizontal features. Features BELOW the glare blob bottom edge are likely external mounting hardware — ignore them. Only consider features WITHIN or AT the edges of the glare blob.

STEP 4 - Identify the real float:
- If glare blob spans top-to-1/2 or larger: float ≈ center of the glare blob.
- If glare blob is small (only near top 20%): find the dark horizontal band just below the glare.
- If visible on tube walls within the glare: that confirms the float position.
Express the float position relative to the text label anchors.

STEP 5 - Calculate percentage:
- EXACTLY at EMPTY marker = 0%
- EXACTLY at 1/4 marker = 25%
- EXACTLY at 1/2 marker = 50%
- EXACTLY at 3/4 marker = 75%
- EXACTLY at FULL marker = 100%

STEP 5 - Calculate percentage:
- EXACTLY at EMPTY marker = 0%
- EXACTLY at 1/4 marker = 25%
- EXACTLY at 1/2 marker = 50%
- EXACTLY at 3/4 marker = 75%
- EXACTLY at FULL marker = 100%

SNAPPING RULE: If the float appears to be touching, straddling, or within roughly 1/8 of the inter-marker spacing from a labeled marker, report that marker's exact value. The float disc has physical thickness — its center being slightly above a line still means the level IS at that line.

RESPOND WITH:
Observations: [List what you see from bottom to top — specifically note whether each feature is bright/reflective (artifact) or dark/solid (potential float)]
Float position: [where is the dark solid band you identified as the real float]
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
