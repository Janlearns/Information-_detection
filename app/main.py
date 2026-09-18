from pathlib import Path
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from app.context_scan import scan
from app.crawler import crawl
from app.classifier import classify, MODEL_ID

app = FastAPI(title="CekFakta AI", version="0.1.0")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")
_job = threading.Lock()
_scan_pool = ThreadPoolExecutor(max_workers=1)
_scan_jobs = {}
_scan_jobs_lock = threading.Lock()

class ScanRequest(BaseModel):
    kind: Literal['text', 'image', 'video']
    text: str = Field(default='', max_length=30000)
    frame: str = Field(default='', max_length=2800000)
    media_note: str = Field(default='', max_length=500)
    linked_terms: list[str] = Field(default_factory=list, max_length=20)

@app.post('/api/scan/jobs')
def start_context_scan(request: ScanRequest):
    if request.kind == 'text' and not request.text.strip():
        raise HTTPException(422, 'Pilih teks yang ingin diperiksa.')
    if not _job.acquire(blocking=False):
        raise HTTPException(429, 'Scan lain sedang berjalan. Tunggu hingga selesai.')
    def work():
        try:
            return scan(request)
        finally:
            _job.release()
    try:
        with _scan_jobs_lock:
            for key, (created, future) in list(_scan_jobs.items()):
                if future.done() and time.monotonic() - created > 300:
                    del _scan_jobs[key]
            job_id = uuid.uuid4().hex
            _scan_jobs[job_id] = (time.monotonic(), _scan_pool.submit(work))
        return {'id': job_id}
    except Exception:
        _job.release()
        raise

@app.get('/api/scan/jobs/{job_id}')
def get_context_scan(job_id: str):
    with _scan_jobs_lock:
        entry = _scan_jobs.get(job_id)
    if entry is None:
        raise HTTPException(404, 'Scan tidak ditemukan; coba scan lagi.')
    future = entry[1]
    if not future.done():
        return {'status': 'running'}
    try:
        return {'status': 'done', 'result': future.result()}
    except Exception as exc:
        raise HTTPException(503, 'Analisis gagal. Periksa server lokal dan coba lagi.') from exc

@app.post('/api/scan')
def context_scan(request: ScanRequest):
    if request.kind == 'text' and not request.text.strip():
        raise HTTPException(422, 'Pilih teks yang ingin diperiksa.')
    if not _job.acquire(blocking=False):
        raise HTTPException(429, 'Scan lain sedang berjalan. Tunggu hingga selesai.')
    try:
        return scan(request)
    finally:
        _job.release()

class AnalyzeRequest(BaseModel):
    url: str = Field(default="", max_length=2048)
    text: str = Field(default="", max_length=30000)
    max_pages: int = Field(default=1, ge=1, le=5)

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL_ID, "model_loading": "lazy"}

@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    if bool(request.url.strip()) == bool(request.text.strip()):
        raise HTTPException(422, "Isi salah satu: URL atau teks.")
    if request.text and len(request.text.strip()) < 100:
        raise HTTPException(422, "Masukkan setidaknya 100 karakter teks.")
    if not _job.acquire(blocking=False):
        raise HTTPException(429, "Analisis lain sedang berjalan. Coba lagi setelah selesai.")
    try:
        if request.url:
            articles, errors = crawl(request.url.strip(), request.max_pages)
        else:
            articles, errors = [{"url": None, "title": "Teks yang Anda masukkan", "text": request.text.strip()}], []
        for article in articles:
            article["analysis"] = classify(article["text"])
        return {"articles": articles, "errors": errors}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(502, "Tidak dapat mengakses situs: " + str(exc)) from exc
    finally:
        _job.release()
