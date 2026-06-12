FROM python:3.11-slim

# Install system dependencies needed for compiling certain python binary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source files
COPY . .

# Ensure logs folder exists
RUN mkdir -p logs

EXPOSE 5000

# Set run command to Gunicorn configuration
CMD ["gunicorn", "-c", "gunicorn.conf.py", "--factory", "app:create_app"]
