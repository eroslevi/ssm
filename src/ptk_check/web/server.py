from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, validator

from ..orchestrator import run_check
from ..reporter import build_report
from ..parser import parse_ptk
from ..indexer import build_index

app = FastAPI(title="PTK Compliance Checker")

_HTML = Path(__file__).parent / "index.html"


class CheckRequest(BaseModel):
    statement: str

    @validator("statement")
    def _len(cls, v: str) -> str:
        if len(v) > 2000:
            raise ValueError("Statement must be ≤ 2,000 characters")
        return v.strip()


class IngestRequest(BaseModel):
    file_path: str


@app.get("/", response_class=HTMLResponse)
def ui() -> str:
    return _HTML.read_text(encoding="utf-8")


@app.post("/check")
def check(req: CheckRequest) -> JSONResponse:
    state  = run_check(req.statement, escalate=False)
    report = build_report(state)
    return JSONResponse(report)


@app.post("/escalate")
def escalate(req: CheckRequest) -> JSONResponse:
    state  = run_check(req.statement, escalate=True)
    report = build_report(state)
    return JSONResponse(report)


@app.post("/ingest")
def ingest(req: IngestRequest) -> JSONResponse:
    import time
    p = Path(req.file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")
    t0       = time.time()
    articles = parse_ptk(str(p))
    build_index(articles)
    return JSONResponse({
        "status":     "ok",
        "articles":   len(articles),
        "duration_s": round(time.time() - t0, 1),
    })
