# Use Python 3.12 as base to ensure compatibility with audio/standard libraries
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if any needed for audio processing basics)
# libasound2-dev might be needed for some audio libs, but usually not for pure numpy/scipy processing
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (Cloud Run defaults to 8080, but we can configure it)
EXPOSE 8080

# Command to run the application
# We listen on 0.0.0.0 and port 8080 (standard for Cloud Run)
CMD ["uvicorn", "bridge.telephony:app", "--host", "0.0.0.0", "--port", "8080"]
