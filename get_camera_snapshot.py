import os
import requests
from dotenv import load_dotenv

load_dotenv()

# UniFi Protect credentials from .env file
UNIFI_HOST = os.getenv("UNIFI_HOST")  # e.g., "192.168.1.1" or "unifi-protect.local"
UNIFI_API_KEY = os.getenv("UNIFI_API_KEY")
CAMERA_ID = os.getenv("CAMERA_ID")  # The ID of the camera you want to snapshot

# Disable SSL warnings
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_unifi_snapshot(output_filename="camera_snapshot.jpg"):
    """
    Connect to UniFi Protect and download a snapshot from a camera.

    Args:
        output_filename: Where to save the snapshot image

    Returns:
        True if successful, False otherwise
    """
    if not all([UNIFI_HOST, UNIFI_API_KEY, CAMERA_ID]):
        print("Error: Missing required environment variables")
        print("Please set: UNIFI_HOST, UNIFI_API_KEY, CAMERA_ID")
        return False

    try:
        print(f"Connecting to UniFi Protect at {UNIFI_HOST}...")

        # Get the snapshot from the camera using API key authentication
        # Using the integration API v1 endpoint
        snapshot_url = f"https://{UNIFI_HOST}/proxy/protect/integration/v1/cameras/{CAMERA_ID}/snapshot"

        headers = {"X-API-KEY": UNIFI_API_KEY, "Accept": "*/*"}

        print(f"Fetching snapshot from camera {CAMERA_ID}...")
        response = requests.get(
            snapshot_url, headers=headers, verify=False, stream=True, timeout=10
        )

        print(f"Response status: {response.status_code}")

        if response.status_code != 200:
            print(f"Failed to get snapshot with status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

        # Save the snapshot to a file
        with open(output_filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Snapshot saved to {output_filename}")
        return True

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {UNIFI_HOST}")
        print("Make sure the host is correct and accessible from your network")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = get_unifi_snapshot("oil_camera_snapshot.jpg")
    if success:
        print("\n✓ Snapshot retrieved successfully!")
    else:
        print("\n✗ Failed to retrieve snapshot")
