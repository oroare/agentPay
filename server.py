from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import ROOT
from merchant.catalog_api import router as catalog_router
from orchestrator.run_session import run_session

app = FastAPI(title="Agentic Commerce Demo", version="1.0.0")
app.include_router(catalog_router)


class RunRequest(BaseModel):
    goal: str = Field(min_length=3)
    max_total_spend_inr: float = Field(gt=0)
    max_upsell_amount_inr: float = Field(default=500, gt=0)
    enable_upsell: bool = True
    simulate_decline: bool = False


@app.post("/api/run")
def api_run(body: RunRequest) -> dict:
    result = run_session(
        goal=body.goal,
        max_total_spend_inr=body.max_total_spend_inr,
        max_upsell_amount_inr=body.max_upsell_amount_inr,
        enable_upsell=body.enable_upsell,
        simulate_decline=body.simulate_decline,
    )
    return result.__dict__


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


frontend = ROOT / "frontend"
app.mount("/static", StaticFiles(directory=frontend), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(frontend / "index.html")
