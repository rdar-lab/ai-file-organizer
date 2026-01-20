# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY setup.py .
COPY README.md .
COPY docker_runner.py .

# Install the package
RUN pip install -e .

# Create directories for input/output
RUN mkdir -p /input /output

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command - run in continuous mode with config file
CMD ["python3", "/app/docker_runner.py"]
