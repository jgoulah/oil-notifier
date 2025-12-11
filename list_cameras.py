import os
import requests
from dotenv import load_dotenv

load_dotenv()

UNIFI_HOST = os.getenv("UNIFI_HOST")
UNIFI_API_KEY = os.getenv("UNIFI_API_KEY")

# Disable SSL warnings
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def list_cameras():
    """List all cameras in UniFi Protect with their IDs and names."""
    if not all([UNIFI_HOST, UNIFI_API_KEY]):
        print("Error: Missing required environment variables")
        print("Please set: UNIFI_HOST, UNIFI_API_KEY")
        return

    try:
        print(f"Connecting to UniFi Protect at {UNIFI_HOST}...")

        # Get cameras using the integration API v1 endpoint
        cameras_url = f"https://{UNIFI_HOST}/proxy/protect/integration/v1/cameras"

        headers = {"X-API-KEY": UNIFI_API_KEY, "Accept": "application/json"}

        response = requests.get(cameras_url, headers=headers, verify=False, timeout=10)

        print(f"Response status: {response.status_code}")

        if response.status_code != 200:
            print(f"Failed to get cameras with status {response.status_code}")
            print(f"Response body: {response.text[:500]}")
            return

        print("Successfully connected!\n")

        # The response is a list of cameras directly
        cameras = response.json()

        if not cameras or len(cameras) == 0:
            print("No cameras found!")
            return

        print(f"Found {len(cameras)} camera(s):\n")
        print("-" * 80)

        for cam in cameras:
            print(f"Name: {cam.get('name', 'Unknown')}")
            print(f"ID: {cam.get('id')}")
            print(f"Model: {cam.get('model', 'Unknown')}")
            print(f"State: {cam.get('state', 'Unknown')}")
            print(f"MAC: {cam.get('mac', 'Unknown')}")
            print("-" * 80)

        print(
            "\nCopy the ID of the camera you want to use and add it to your .env file as CAMERA_ID"
        )

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    list_cameras()
