FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN mkdir -p /app/data/uploaded \
    /app/data/processing \
    /app/data/processed \
    /app/data/failed

CMD ["python", "-m", "fsae_parser.main"]