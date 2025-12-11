# Oil Level Notifier

Automated oil tank level monitoring using UniFi Protect camera and Claude AI vision analysis.

## Features

- 📷 Grabs snapshots from UniFi Protect camera
- 🤖 Analyzes oil gauge using Claude AI vision
- 📊 Logs all readings to CSV file
- 📧 Email alerts when oil drops below 25%
- 💾 Saves all snapshots to `images/` directory

## Setup

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install anthropic python-dotenv Pillow requests
```

### 2. Configure Environment Variables

Create a `.env` file with:

```bash
# UniFi Protect Configuration
UNIFI_HOST=your-unifi-host
UNIFI_API_KEY=your-api-key
CAMERA_ID=your-camera-id

# Anthropic API
ANTHROPIC_API_KEY=your-anthropic-api-key

# Email/SMTP Configuration (optional - defaults to localhost:25)
SMTP_SERVER=localhost
SMTP_PORT=25
```

### 3. Generate UniFi Protect API Key

1. Log into UniFi Protect web interface
2. Go to Settings → Integrations
3. Create a new API key
4. Copy the key to `UNIFI_API_KEY` in `.env`

### 4. Find Camera ID

```bash
python3 list_cameras.py
```

Copy the ID of your oil gauge camera to `CAMERA_ID` in `.env`.

### 5. Get Anthropic API Key

1. Go to https://console.anthropic.com/settings/keys
2. Create a new API key
3. Add billing/credits if needed
4. Copy to `ANTHROPIC_API_KEY` in `.env`

## Usage

### Check Oil Level Once

```bash
python3 check_oil_level.py
```

This will:
- Grab a snapshot from the camera
- Analyze the gauge with Claude
- Save the image to `images/`
- Log the reading to `oil_level_log.csv`
- Send email alert if oil is below 25%

### Schedule Automated Checks

Add to crontab to check daily at 8 AM:

```bash
crontab -e
```

Add:
```
0 8 * * * cd /Users/jgoulah/dev/oil-notifier && /Users/jgoulah/dev/oil-notifier/.venv/bin/python3 check_oil_level.py
```

## Configuration

### Alert Threshold

Edit `check_oil_level.py` to change the alert threshold (default: 25%):

```python
ALERT_THRESHOLD = 25  # Alert when oil level drops below this percentage
```

### Email Address

Email alerts are sent to `jgoulah@gmail.com` by default. To change, edit:

```python
ALERT_EMAIL = "your-email@example.com"
```

## Files

- `check_oil_level.py` - Main script
- `list_cameras.py` - List available cameras  
- `get_camera_snapshot.py` - Helper for camera snapshots
- `oil_level_log.csv` - Reading history
- `images/` - Snapshot storage
- `test/` - Test and diagnostic scripts
- `.env` - Configuration (not in git)

## Troubleshooting

### Email Not Sending

The script uses localhost SMTP by default. To use an external SMTP server, add to `.env`:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

Then update the script to use authentication.

### Inaccurate Readings

The system is calibrated for readings within ±5-10%. If readings are consistently off:

1. Check camera angle hasn't changed
2. Review saved images in `images/` directory
3. Adjust crop coordinates if needed (see `test/crop_gauge.py`)

## Cost Estimate

- UniFi Protect API: Free
- Anthropic Claude Sonnet: ~$0.01-0.02 per reading
- Daily checks: ~$0.30-0.60/month
# oil-notifier
