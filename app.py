from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from harness.runner import run_eval

ROOT = Path(__file__).parent.resolve()
CASES_DIR = ROOT / "cases"
OUT_DIR = ROOT / "out"

app = FastAPI(title="TruthSeek Eval Harness", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(ROOT / "web" / "static")), name="static")


class RunRequest(BaseModel):
    category: Optional[str] = None
    strict: bool = False
    config_path: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (ROOT / "web" / "index.html").read_text(encoding="utf-8")


@app.get("/api/cases")
def list_cases() -> dict:
    items = []
    for p in sorted(CASES_DIR.rglob("*.y*ml")):
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        rows = raw.get("cases", [raw]) if isinstance(raw, dict) else raw
        for row in rows:
            if not row:
                continue
            items.append({
                "id": row.get("id"),
                "title": row.get("title"),
                "category": row.get("category"),
                "expect": row.get("expect"),
                "file": str(p.relative_to(ROOT)),
            })
    return {"cases": items}


@app.post("/api/run")
async def run(req: RunRequest) -> JSONResponse:
    try:
        scorecard = await run_eval(CASES_DIR, config_path=req.config_path, category=req.category, strict=req.strict, out_dir=OUT_DIR)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(scorecard.to_dict())


@app.post("/api/upload-cases")
async def upload_cases(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.endswith((".yaml", ".yml")):
        raise HTTPException(status_code=400, detail="Upload a .yaml or .yml case file")
    dest = CASES_DIR / Path(file.filename).name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True, "path": str(dest.relative_to(ROOT))}


@app.post("/api/add-case")
async def add_case(case_yaml: str = Form(...), filename: str = Form("custom_cases.yaml")) -> dict:
    try:
        parsed = yaml.safe_load(case_yaml)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {exc}") from exc
    if not parsed:
        raise HTTPException(status_code=400, detail="Case YAML is empty")
    dest = CASES_DIR / Path(filename).name
    existing = []
    if dest.exists():
        raw = yaml.safe_load(dest.read_text(encoding="utf-8")) or {}
        existing = raw.get("cases", [raw]) if isinstance(raw, dict) else raw
    new_rows = parsed.get("cases", [parsed]) if isinstance(parsed, dict) else parsed
    dest.write_text(yaml.safe_dump({"cases": existing + new_rows}, sort_keys=False), encoding="utf-8")
    return {"ok": True, "path": str(dest.relative_to(ROOT))}


@app.get("/api/scorecard")
def scorecard_json() -> FileResponse:
    path = OUT_DIR / "scorecard.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No scorecard yet. Run the harness first.")
    return FileResponse(path, media_type="application/json", filename="scorecard.json")


@app.get("/scorecard", response_class=HTMLResponse)
def scorecard_html() -> HTMLResponse:
    path = OUT_DIR / "scorecard.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No scorecard yet. Run the harness first.")
    return HTMLResponse(path.read_text(encoding="utf-8"))
