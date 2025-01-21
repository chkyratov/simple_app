FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create instance directory for SQLite database
RUN mkdir -p instance

# Create directory for certificates
RUN mkdir -p certs

# Copy SSL certificates
COPY certs/cert.pem certs/cert.pem
COPY certs/key.pem certs/key.pem

# Expose HTTPS port
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]
