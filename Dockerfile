# FROM python:3.10-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1
# ENV PYTHONPATH=/app

# WORKDIR /app

# # Install system dependencies required for psycopg
# RUN apt-get update && apt-get install -y \
#     libpq-dev \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .
# RUN pip3 install --no-cache-dir -r requirements.txt

# COPY . .

# CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "600"]

# EXPOSE 8000


FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies required for psycopg and nginx
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Remove default nginx site config
RUN rm /etc/nginx/sites-enabled/default

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy Django project files
COPY . .

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose the port nginx listens on
EXPOSE 8000

# Start Gunicorn + nginx together
# CMD gunicorn core.wsgi:application --bind 127.0.0.1:9000 --workers 3 --timeout 600 & nginx -g 'daemon off;'
# CMD ["/bin/sh", "-c", "gunicorn core.wsgi:application --bind 127.0.0.1:9000 --workers 3 --timeout 600 & nginx -g 'daemon off;'"]
CMD ["/bin/sh", "-c", "gunicorn core.wsgi:application --bind 127.0.0.1:9000 --workers 3 --timeout 600 --log-level debug & nginx -g 'daemon off;'"]


