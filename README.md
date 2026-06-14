# Formula SAE Telemetry Ingestion Comparison App

This project is a local telemetry ingestion test application for comparing different ways to ingest, store, search, and visualize Formula SAE telemetry data.

The goal is to upload a Formula SAE telemetry file through a local web interface, parse it into a common normalized telemetry format, and then export the same parsed data to multiple backends for comparison.

The initial implementation will focus on:

- Local file upload through a FastAPI web interface
- Python-based telemetry parsing and normalization
- Exporting parsed telemetry rows to Grafana Cloud Loki using the Loki Push API
- Running the local application stack with Docker Compose

Later phases will add:

- Nominal Edge exporter
- Local Elasticsearch exporter
- Local Kibana frontend for Elasticsearch
- Side-by-side evaluation of Grafana Cloud Loki, Nominal Edge, and Elasticsearch/Kibana

---

## High-Level Architecture

```text
Formula SAE telemetry file
        |
        v
+---------------------+
| FastAPI Web UI      |
|                     |
| Uploads raw files   |
| into data/uploaded/ |
+---------------------+
        |
        v
Shared Docker volume
        |
        v
+-----------------------------+
| Python Parser Worker        |
|                             |
| Watches data/uploaded/      |
| Moves files to processing/  |
| Parses telemetry data       |
| Normalizes records          |
| Sends records to exporters  |
+-----------------------------+
        |
        v
+-----------------------------+
| Exporter Layer              |
|                             |
| LokiExporter                |
| NominalExporter             |
| ElasticsearchExporter       |
+-----------------------------+
        |
        +---------------------> Grafana Cloud Loki
        |
        +---------------------> Nominal Edge
        |
        +---------------------> Local Elasticsearch
                                  |
                                  v
                              Kibana
```

---

## Design Goals

The project is designed around a few core principles.

### 1. Keep the parser independent from the backends

The parser should only be responsible for reading Formula SAE files and turning them into a normalized telemetry format.

It should not contain Loki-specific, Nominal-specific, or Elasticsearch-specific logic.

Backend-specific behavior should live in separate exporter modules.

```text
Raw file
  -> parsed telemetry records
  -> normalized telemetry records
  -> exporter-specific formatting
  -> backend upload
```

This makes it easier to add new telemetry backends later without rewriting the parser.

---

### 2. Use a common normalized telemetry model

Each backend should receive the same underlying telemetry information.

Example normalized record:

```json
{
  "timestamp_ns": 1710000000010000000,
  "session_id": "session_001",
  "car": "fsae_demo",
  "subsystem": "battery",
  "channel": "pack_voltage",
  "value": 398.4,
  "units": "V"
}
```

This common format allows fair comparison between Loki, Nominal Edge, and Elasticsearch.

---

### 3. Use a simple local development stack

The first version will use Docker Compose instead of Docker Swarm.

Docker Compose is simpler for a local desktop prototype and is sufficient for running:

- Web upload service
- Parser worker service
- Shared file volume
- Later: Elasticsearch and Kibana

Docker Swarm can be considered later if the project needs cluster-style orchestration.

---

### 4. Use explicit file lifecycle folders

Uploaded files move through a simple local file lifecycle.

```text
data/
  uploaded/
  processing/
  processed/
  failed/
```

The web interface writes files into `data/uploaded/`.

The parser worker moves files into `data/processing/` before parsing them. This prevents the parser from reading a file while the web app is still writing it.

After parsing and export:

- Successfully handled files move to `data/processed/`
- Files that fail parsing or export move to `data/failed/`

---

## Initial Data Flow

```text
1. User opens local FastAPI web page.
2. User uploads a Formula SAE telemetry file.
3. Web app saves the file to data/uploaded/.
4. Parser worker detects the new file.
5. Parser worker moves file to data/processing/.
6. Parser reads and normalizes the telemetry records.
7. Parser sends normalized records to enabled exporters.
8. Loki exporter batches records and pushes them to Grafana Cloud Loki.
9. Parser moves the file to data/processed/ if successful.
10. Parser moves the file to data/failed/ if parsing or export fails.
```

---

## Planned Repository Layout

```text
fsae-telemetry-ingestion/
  README.md
  docker-compose.yml
  .env.example
  .gitignore

  data/
    uploaded/
      .gitkeep
    processing/
      .gitkeep
    processed/
      .gitkeep
    failed/
      .gitkeep

  services/
    web/
      Dockerfile
      pyproject.toml
      src/
        web_app/
          __init__.py
          main.py
          templates/
            upload.html
            status.html
          static/
            styles.css

    parser/
      Dockerfile
      pyproject.toml
      src/
        fsae_parser/
          __init__.py
          main.py

          config.py
          models.py
          file_watcher.py
          file_lifecycle.py

          parsers/
            __init__.py
            base.py
            fsae_binary_parser.py
            jsonl_parser.py

          normalizers/
            __init__.py
            telemetry_normalizer.py

          exporters/
            __init__.py
            base.py
            loki_exporter.py
            nominal_exporter.py
            elasticsearch_exporter.py

          utils/
            __init__.py
            logging.py
            time.py

      tests/
        test_file_lifecycle.py
        test_normalizer.py
        test_loki_exporter.py

  docs/
    architecture.md
    data_model.md
    backend_comparison.md
```

---

## Service Responsibilities

### Web Service

The web service provides a simple local browser interface for uploading Formula SAE telemetry files.

Recommended technology:

```text
FastAPI + Jinja2 templates
```

Responsibilities:

- Serve local upload page
- Accept file uploads
- Save uploaded files to `data/uploaded/`
- Show basic file status
- Avoid parsing telemetry files directly

Example routes:

```text
GET  /             Upload page
POST /upload       Upload Formula SAE telemetry file
GET  /status       Show uploaded, processing, processed, and failed files
GET  /health       Health check endpoint
```

---

### Parser Worker Service

The parser worker is a long-running Python process.

Responsibilities:

- Watch `data/uploaded/` for new files
- Move files into `data/processing/`
- Parse Formula SAE telemetry files
- Normalize parsed samples into a common record format
- Send normalized records to enabled exporters
- Move completed files into `data/processed/`
- Move failed files into `data/failed/`

The parser should be backend-neutral.

It should not directly know how Loki, Nominal Edge, or Elasticsearch store data. It should only pass normalized records to exporter classes.

---

### Exporter Layer

The exporter layer is responsible for converting normalized telemetry records into backend-specific payloads.

Initial exporter:

```text
LokiExporter
```

Future exporters:

```text
NominalExporter
ElasticsearchExporter
```

Exporter interface concept:

```python
class TelemetryExporter:
    def export(self, records: list[TelemetryRecord]) -> None:
        raise NotImplementedError
```

The parser can then run all enabled exporters:

```python
for exporter in enabled_exporters:
    exporter.export(records)
```

---

## Loki Export Design

The first backend will be Grafana Cloud Loki.

The Loki exporter will use the Loki Push API.

Recommended Loki label strategy:

```text
app="fsae-uploader"
car="fsae_demo"
session_id="session_001"
subsystem="battery"
```

The changing telemetry fields should stay in the JSON log body:

```json
{
  "channel": "pack_voltage",
  "value": 398.4,
  "units": "V"
}
```

The Loki payload will group records into streams based on common labels.

Example Loki stream:

```json
{
  "streams": [
    {
      "stream": {
        "app": "fsae-uploader",
        "car": "fsae_demo",
        "session_id": "session_001",
        "subsystem": "battery"
      },
      "values": [
        [
          "1710000000010000000",
          "{\"channel\":\"pack_voltage\",\"value\":398.4,\"units\":\"V\"}"
        ]
      ]
    }
  ]
}
```

Important note: Loki timestamps should be sent as strings containing epoch nanoseconds.

---

## Environment Variables

The app will use environment variables for backend configuration.

Example `.env.example`:

```env
# General
APP_ENV=local
DATA_ROOT=/app/data
ENABLED_EXPORTERS=loki

# Grafana Cloud Loki
GRAFANA_LOKI_PUSH_URL=https://logs-prod-000.grafana.net/loki/api/v1/push
GRAFANA_LOKI_USER=your_loki_user_or_instance_id
GRAFANA_CLOUD_TOKEN=your_grafana_cloud_token

# Future: Nominal Edge
NOMINAL_ENABLED=false
NOMINAL_API_URL=
NOMINAL_API_TOKEN=

# Future: Elasticsearch
ELASTICSEARCH_ENABLED=false
ELASTICSEARCH_URL=http://elasticsearch:9200
ELASTICSEARCH_INDEX=fsae-telemetry
```

---

## Docker Compose Design

The first version of the stack will run two containers:

```text
web
parser
```

Both containers will mount the same local `data/` folder.

Planned first-draft `docker-compose.yml` structure:

```yaml
services:
  web:
    build:
      context: ./services/web
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env

  parser:
    build:
      context: ./services/parser
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    depends_on:
      - web
```

Future Elasticsearch/Kibana services:

```yaml
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.x.x
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.x.x
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

Elasticsearch and Kibana are intentionally deferred until after the Loki path is working.

---

## Planned Development Phases

### Phase 1: Local upload and file lifecycle

Build the basic local app.

Includes:

- Docker Compose setup
- FastAPI upload page
- Shared `data/` volume
- File lifecycle folders
- Parser worker that detects files and moves them through the lifecycle
- Simple mock parser or JSONL parser

Success criteria:

```text
Upload file through browser
File appears in data/uploaded/
Parser moves it to data/processing/
Parser moves it to data/processed/
Failed files move to data/failed/
```

---

### Phase 2: Formula SAE parser and normalizer

Implement the parser for the Formula SAE telemetry file format.

Includes:

- Parse uploaded Formula SAE files
- Extract battery, motor, pedals, and vehicle dynamics channels
- Normalize all channels into common telemetry records
- Add parser tests

Success criteria:

```text
Uploaded Formula SAE file produces normalized telemetry records
Records include timestamp_ns, session_id, subsystem, channel, value, and units
```

---

### Phase 3: Loki exporter

Implement the Grafana Cloud Loki exporter.

Includes:

- Loki Push API client
- Batching
- Stream grouping by label set
- Basic retry/error handling
- Grafana Explore query examples

Success criteria:

```text
Uploaded Formula SAE file appears in Grafana Cloud Loki
Telemetry can be queried in Grafana Explore using LogQL
```

Example LogQL:

```logql
{app="fsae-uploader", session_id="session_001"}
```

```logql
{app="fsae-uploader", session_id="session_001", subsystem="battery"}
| json
| channel="pack_voltage"
```

---

### Phase 4: Nominal Edge exporter

Add support for exporting normalized Formula SAE telemetry records to Nominal Edge.

Includes:

- Nominal-specific exporter module
- Mapping normalized telemetry records to Nominal's expected ingestion format
- Configuration for Nominal API/Edge endpoint
- Side-by-side comparison with Loki

Success criteria:

```text
The same uploaded Formula SAE file can be exported to both Loki and Nominal Edge
```

---

### Phase 5: Elasticsearch and Kibana

Add local Elasticsearch and Kibana containers.

Includes:

- Elasticsearch service
- Kibana service
- Elasticsearch exporter
- Index mapping for Formula SAE telemetry records
- Basic Kibana dashboard or Discover workflow

Success criteria:

```text
The same uploaded Formula SAE file can be exported to Loki and Elasticsearch
Telemetry can be searched in Kibana
```

---

## Backend Comparison Goals

The project will eventually compare each backend across several dimensions.

| Backend | Main Question |
|---|---|
| Grafana Cloud Loki | How well does log-based telemetry ingestion work for Formula SAE data? |
| Nominal Edge | How well does an engineering/test-data platform handle the same telemetry? |
| Elasticsearch/Kibana | How well does document indexing and search work for telemetry analysis? |

Evaluation dimensions:

- Ease of ingestion
- Data modeling complexity
- Query experience
- Dashboarding experience
- Handling of timestamps
- Handling of high-cardinality fields
- Searchability
- Local development complexity
- Operational complexity
- Fit for engineering telemetry workflows

---

## First Version Scope

The first implementation should stay focused.

Included:

- FastAPI local upload app
- Parser worker container
- Shared `data/` folder
- Four lifecycle folders
- Common normalized telemetry model
- Loki exporter
- Docker Compose

Not included yet:

- Nominal Edge
- Elasticsearch
- Kibana
- Docker Swarm
- Production authentication flows
- User accounts
- Database-backed job tracking
- Advanced dashboard generation

---

## Running the App

Planned local startup command:

```bash
docker compose up --build
```

Then open the local web interface:

```text
http://localhost:8000
```

Upload a Formula SAE telemetry file and check the local data folders:

```text
data/uploaded/
data/processing/
data/processed/
data/failed/
```

After Loki export is configured, check Grafana Cloud Explore with LogQL:

```logql
{app="fsae-uploader"}
```

---

## Notes

This project is intentionally designed as a comparison harness rather than a single-backend uploader.

The most important architectural decision is to keep the telemetry parser, normalized data model, and exporters separate.

That separation allows the same Formula SAE telemetry file to be sent to multiple backends without rewriting the parsing logic.
