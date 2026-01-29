#!/usr/bin/env python3
"""Debug network connectivity to UniFi Protect."""
import os
import socket
import requests
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

UNIFI_HOST = os.getenv("UNIFI_HOST")
UNIFI_API_KEY = os.getenv("UNIFI_API_KEY")
CAMERA_ID = os.getenv("CAMERA_ID")

print(f"UNIFI_HOST: {UNIFI_HOST}")
print(f"CAMERA_ID: {CAMERA_ID}")
print()

# Check DNS resolution
print("=== DNS Resolution ===")
try:
    ip = socket.gethostbyname(UNIFI_HOST)
    print(f"{UNIFI_HOST} resolves to: {ip}")
except Exception as e:
    print(f"DNS resolution failed: {e}")

print()

# Test with different approaches
snapshot_url = f"https://{UNIFI_HOST}/proxy/protect/integration/v1/cameras/{CAMERA_ID}/snapshot"

print("=== Test 1: Default Python requests ===")
try:
    response = requests.get(
        snapshot_url,
        headers={"X-API-KEY": UNIFI_API_KEY, "Accept": "*/*"},
        verify=False,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Body: {response.text[:200]}")
    else:
        print(f"Success! Got {len(response.content)} bytes")
except Exception as e:
    print(f"Error: {e}")

print()

print("=== Test 2: With curl-like User-Agent ===")
try:
    response = requests.get(
        snapshot_url,
        headers={
            "X-API-KEY": UNIFI_API_KEY,
            "Accept": "*/*",
            "User-Agent": "curl/7.79.1"
        },
        verify=False,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Body: {response.text[:200]}")
    else:
        print(f"Success! Got {len(response.content)} bytes")
except Exception as e:
    print(f"Error: {e}")

print()

# Try with IP if we got one
try:
    ip = socket.gethostbyname(UNIFI_HOST)
    print(f"=== Test 3: Using IP ({ip}) instead of hostname ===")
    ip_url = f"https://{ip}/proxy/protect/integration/v1/cameras/{CAMERA_ID}/snapshot"
    response = requests.get(
        ip_url,
        headers={
            "X-API-KEY": UNIFI_API_KEY,
            "Accept": "*/*",
            "Host": UNIFI_HOST  # Send original hostname in Host header
        },
        verify=False,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Body: {response.text[:200]}")
    else:
        print(f"Success! Got {len(response.content)} bytes")
except Exception as e:
    print(f"Error: {e}")
