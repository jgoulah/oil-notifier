import base64
import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL_NAME = "claude-sonnet-4-5"

with open("./oil.png", "rb") as image_file:
    binary_data = image_file.read()
    base_64_encoded_data = base64.b64encode(binary_data)
    base64_string = base_64_encoded_data.decode("utf-8")


message_list = [
    {
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64_string,
                },
            },
            {
                "type": "text",
                "text": "evaluate this image and tell me what percentage the gauge is",
            },
        ],
    }
]

response = client.messages.create(
    model=MODEL_NAME, max_tokens=2048, messages=message_list
)
print(response.content[0].text)
