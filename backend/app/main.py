from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import machine_csv_path
from app.database.db import ensure_default_machine, init_db, persist_inference
from app.routers.api import router
from app.services.replay import ReplayEngine


app = FastAPI(
    title="Industrial Monitor API",
    description="API para monitoramento de máquinas industriais legadas.",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


replay = ReplayEngine()


@app.on_event("startup")
def startup() -> None:
    init_db()

    machine = ensure_default_machine()

    machine_csv_path(machine["id"]).touch(exist_ok=True)

    async def persist(item: dict):
        persist_inference(item)

    replay.subscribe(persist)


app.include_router(router)


@app.get("/")
def root():
    return {
        "service": "industrial-monitor",
        "machine": "Máquina 01",
        "docs": "/docs",
    }