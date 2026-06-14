FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency/build metadata first for better Docker layer caching
COPY pyproject.toml ./

# Copy Loki exporter source code
COPY src ./src

# Install the Loki exporter package
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Create shared data folder mount points used by docker-compose
RUN mkdir -p /app/data/normalized \
    /app/data/export_status/loki/exported \
    /app/data/export_status/loki/failed

# Run the Loki exporter worker
CMD ["python", "-m", "loki_exporter.main"]