FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    gettext \
    git \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Create app user and group
RUN groupadd -r nexus && useradd -r -g nexus nexus

# Set work directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs && \
    chown -R nexus:nexus /app

# Copy and install Python dependencies
COPY backend/requirements/ /app/requirements/
RUN pip install --upgrade pip && \
    pip install -r requirements/development.txt

# Copy entrypoint script
COPY docker/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown nexus:nexus /entrypoint.sh

# Copy application code
COPY backend/ /app/
RUN chown -R nexus:nexus /app

# Switch to non-root user
USER nexus

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]