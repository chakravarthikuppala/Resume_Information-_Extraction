from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from nlp.extractor import extract_resume
from nlp.text_extract import SUPPORTED_EXTENSIONS

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
SAMPLE_DIR = BASE_DIR / "sample"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/extract")
def api_extract():
    uploaded = request.files.get("resume")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Upload a PDF, DOCX, or TXT resume."}), 400

    suffix = Path(uploaded.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return jsonify({"error": f"Unsupported type {suffix}. Use PDF, DOCX, or TXT."}), 400

    saved = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    uploaded.save(saved)
    try:
        result = extract_resume(str(saved), filename=uploaded.filename)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception:
        app.logger.exception("Resume extraction failed")
        return jsonify({"error": "The resume could not be processed. Check the file and try again."}), 500
    finally:
        try:
            saved.unlink(missing_ok=True)
        except OSError:
            pass
    return jsonify(result)


@app.get("/api/sample")
def api_sample():
    sample = SAMPLE_DIR / "sample_resume.txt"
    if not sample.exists():
        return jsonify({"error": "Sample resume is missing."}), 404
    result = extract_resume(str(sample), filename=sample.name)
    return jsonify(result)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/favicon.ico")
def favicon():
    return send_from_directory(BASE_DIR / "static", "favicon.ico", max_age=0)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)
