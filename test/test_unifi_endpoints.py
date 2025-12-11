import os
import requests
from dotenv import load_dotenv

load_dotenv()

UNIFI_HOST = os.getenv("UNIFI_HOST")
UNIFI_API_KEY = os.getenv("UNIFI_API_KEY")

# Disable SSL warnings
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def test_endpoint(url, description, with_api_key=True):
    """Test if an endpoint is accessible with API key."""
    print(f"\nTesting: {description}")
    print(f"URL: {url}")

    headers = {}
    if with_api_key and UNIFI_API_KEY:
        headers["X-API-KEY"] = UNIFI_API_KEY
        headers["Accept"] = "application/json"
        print("Using API key authentication")

    try:
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            print("✓ Success! This endpoint is accessible")
            # Try to show a preview of the response
            try:
                if "application/json" in response.headers.get("Content-Type", ""):
                    data = response.json()
                    print(f"Response preview: {str(data)[:300]}...")
                else:
                    print(f"Content-Type: {response.headers.get('Content-Type')}")
                    print(f"Content length: {len(response.content)} bytes")
            except:
                pass
        elif response.status_code == 401:
            print("✓ Endpoint exists but requires authentication")
        elif response.status_code == 403:
            print("✓ Endpoint exists but access forbidden")
        elif response.status_code == 404:
            print("✗ Endpoint not found")
            print(f"Response: {response.text[:300]}")
        else:
            print(f"Response: {response.text[:300] if response.text else 'No content'}")

    except requests.exceptions.Timeout:
        print("✗ Timeout - endpoint not responding")
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    if not UNIFI_HOST:
        print("Error: UNIFI_HOST not set in .env file")
        exit(1)

    if not UNIFI_API_KEY:
        print("Warning: UNIFI_API_KEY not set - some tests may fail")

    print(f"Testing UniFi Protect endpoints at: {UNIFI_HOST}")
    print("=" * 80)

    # Test the example endpoint from the curl command
    endpoints = [
        (
            f"https://{UNIFI_HOST}/proxy/protect/integration/v1/meta/info",
            "Integration API - Meta Info (from curl example)",
            True,
        ),
        (
            f"https://{UNIFI_HOST}/proxy/protect/api/bootstrap",
            "Bootstrap API (old method)",
            True,
        ),
        (
            f"https://{UNIFI_HOST}/proxy/protect/api/cameras",
            "Cameras API (old method)",
            True,
        ),
        (
            f"https://{UNIFI_HOST}/proxy/protect/integration/v1/bootstrap",
            "Integration API - Bootstrap",
            True,
        ),
        (
            f"https://{UNIFI_HOST}/proxy/protect/integration/v1/cameras",
            "Integration API - Cameras",
            True,
        ),
    ]

    for url, description, use_key in endpoints:
        test_endpoint(url, description, use_key)

    print("\n" + "=" * 80)
    print("\nWe'll use whichever endpoint returns 200 OK")
