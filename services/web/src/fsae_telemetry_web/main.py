from pathlib import Path
from uuid import uuid4
import json
import shutil

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse


DATA_ROOT = Path("/app/data")
UPLOADED_DIR = DATA_ROOT / "uploaded"
PROCESSING_DIR = DATA_ROOT / "processing"
PROCESSED_DIR = DATA_ROOT / "processed"
FAILED_DIR = DATA_ROOT / "failed"
NORMALIZED_DIR = DATA_ROOT / "normalized"

VALID_OUTPUT_FORMATS = {"jsonl", "parquet", "dataframe"}


app = FastAPI(
    title="Formula SAE Telemetry Upload Service",
    description="Local web interface for uploading Formula SAE telemetry files.",
    version="0.1.0",
)


def ensure_data_dirs() -> None:
    for directory in [
        UPLOADED_DIR,
        PROCESSING_DIR,
        PROCESSED_DIR,
        FAILED_DIR,
        NORMALIZED_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
def startup() -> None:
    ensure_data_dirs()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def upload_page() -> str:
    return """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Formula SAE Telemetry Upload</title>
      </head>
      <body>
        <h1>Formula SAE Telemetry Upload</h1>

        <form action="/upload" enctype="multipart/form-data" method="post">
          <p>
            <label for="file">Telemetry file</label><br>
            <input id="file" name="file" type="file" required>
          </p>

          <p>
            <label for="output_format">Parser output format</label><br>
            <select id="output_format" name="output_format" required>
              <option value="jsonl" selected>JSONL (.jsonl)</option>
              <option value="parquet">Parquet (.parquet)</option>
              <option value="dataframe">Wide DataFrame CSV (.csv)</option>
            </select>
          </p>

          <button type="submit">Upload</button>
        </form>

        <p>
          <a href="/status">View file status</a>
        </p>
      </body>
    </html>
    """


@app.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    output_format: str = Form("jsonl"),
) -> RedirectResponse:
    ensure_data_dirs()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    if output_format not in VALID_OUTPUT_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid output format. "
                "Valid choices are: jsonl, parquet, dataframe."
            ),
        )

    original_name = Path(file.filename).name
    unique_name = f"{uuid4().hex}_{original_name}"

    temp_path = UPLOADED_DIR / f"{unique_name}.tmp"
    final_path = UPLOADED_DIR / unique_name
    metadata_temp_path = UPLOADED_DIR / f"{unique_name}.metadata.json.tmp"
    metadata_final_path = UPLOADED_DIR / f"{unique_name}.metadata.json"

    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        metadata = {
            "original_filename": original_name,
            "stored_filename": unique_name,
            "output_format": output_format,
        }
        metadata_temp_path.write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )

        # Write metadata first and rename the uploaded file last.
        # The parser only watches for telemetry files, so this prevents it from
        # seeing a ready file before its metadata sidecar exists.
        metadata_temp_path.rename(metadata_final_path)
        temp_path.rename(final_path)

    except Exception as exc:
        for path in [temp_path, final_path, metadata_temp_path, metadata_final_path]:
            if path.exists():
                path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {exc}",
        ) from exc

    return RedirectResponse(url="/status", status_code=303)


@app.get("/status", response_class=HTMLResponse)
def status_page() -> str:
    ensure_data_dirs()

    sections = {
        "Uploaded": UPLOADED_DIR,
        "Processing": PROCESSING_DIR,
        "Normalized": NORMALIZED_DIR,
        "Processed": PROCESSED_DIR,
        "Failed": FAILED_DIR,
    }

    html_sections = []

    for title, directory in sections.items():
        files = sorted(
            [
                path.name
                for path in directory.iterdir()
                if (
                    path.is_file()
                    and not path.name.startswith(".")
                    and not path.name.endswith(".tmp")
                    and not path.name.endswith(".metadata.json")
                )
            ]
        )

        if files:
            file_items = "\n".join(f"<li>{name}</li>" for name in files)
        else:
            file_items = "<li><em>No files</em></li>"

        html_sections.append(
            f"""
            <h2>{title}</h2>
            <ul>
              {file_items}
            </ul>
            """
        )

    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <title>Formula SAE Telemetry File Status</title>
      </head>
      <body>
        <h1>Formula SAE Telemetry File Status</h1>

        {''.join(html_sections)}

        <p>
          <a href="/">Upload another file</a>
        </p>
      </body>
    </html>