FROM python:3.12-slim

# Prevent Python from writing .pyc files and force logs to flush immediately
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# App working directory inside the container
WORKDIR /app

# Install system dependencies only if needed later.
# Keeping this minimal for the first FastAPI web service.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project dependency files first for better Docker layer caching
COPY pyproject.toml ./

# Install the web app package and dependencies
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Create the data directory mount point used by docker-compose
RUN mkdir -p /app/data/uploaded \
    /app/data/processing \
    /app/data/normalized \
    /app/data/processed \
    /app/data/failed

# FastAPI port
EXPOSE 8000

# Run the FastAPI app
CMD ["uvicorn", "fsae_telemetry_web.main:app", "--host", "0.0.0.0", "--port", "8000"]