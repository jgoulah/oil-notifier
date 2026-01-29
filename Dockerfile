FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY check_oil_level.py .
COPY list_cameras.py .
COPY get_camera_snapshot.py .
COPY debug_network.py .

# Create directories for data
RUN mkdir -p /app/images

# Run the oil check
CMD ["python", "check_oil_level.py"]
