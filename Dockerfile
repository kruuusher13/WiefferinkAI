# Use Python 3.12 as base to ensure compatibility with audio/standard libraries
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies + MS SQL ODBC Driver 18
# Uses signed-by for Debian Trixie (apt-key is removed)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    gnupg2 \
    unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
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
# bridge.api:app includes the telephony WebSocket router
CMD ["uvicorn", "bridge.api:app", "--host", "0.0.0.0", "--port", "8080"]
