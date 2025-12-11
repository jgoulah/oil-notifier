#!/usr/bin/env python3
"""
Ask Claude to describe what it sees at different parts of the gauge.
This helps us understand what it's interpreting as the float.
"""

import base64
import os
from io import BytesIO

from anthropic import Anthropic
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-sonnet-4-5"


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

    # Convert to bytes
    output = BytesIO()
    img.save(output, format="JPEG", quality=95)
    return output.getvalue()


def ask_claude_to_describe(image_data):
    """Ask Claude to describe what it sees at different parts of the gauge."""
    base64_image = base64.b64encode(image_data).decode("utf-8")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = """This is a vertical oil tank float gauge. I need you to describe what you see at different vertical positions on the gauge.

Please tell me:
1. What do you see at the VERY TOP of the gauge (near where "FULL" should be)?
2. What do you see in the area marked "3/4"?
3. What do you see in the area marked "1/2"?
4. What do you see in the area marked "1/4"?
5. What do you see at the bottom (near "EMPTY")?

For each area, describe:
- Any thick/wide dark bands or sections
- Any thin lines (these are just markers)
- The color/appearance of that section
- Whether you see the float indicator there

Be very specific about WHERE you see thick dark bands vs thin marker lines."""

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
                    "text": prompt,
                },
            ],
        }
    ]

    try:
        response = client.messages.create(
            model=MODEL_NAME, max_tokens=2048, messages=message_list
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python3 debug_what_claude_sees.py <image_path>")
        print(
            "Example: python3 debug_what_claude_sees.py oil_snapshot_20251210_193037.jpg"
        )
        sys.exit(1)

    image_path = sys.argv[1]

    print("Processing image...")
    processed_data = process_image(image_path)

    print("Asking Claude to describe what it sees...\n")
    print("=" * 80)

    result = ask_claude_to_describe(processed_data)
    if result:
        print(result)
        print("=" * 80)
