FROM python:3.9-slim

# Install cron and necessary tools
RUN apt-get update && apt-get install -y \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy cron configuration
COPY docker/cron/crontab /etc/cron.d/eva-updates
RUN chmod 0644 /etc/cron.d/eva-updates && \
    crontab /etc/cron.d/eva-updates

# Create log directory
RUN mkdir -p /app/logs

# Copy and make entrypoint executable
COPY docker/cron/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run cron in foreground
ENTRYPOINT ["/entrypoint.sh"]