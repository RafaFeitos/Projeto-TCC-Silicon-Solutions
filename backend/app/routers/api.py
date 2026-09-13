from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.inference.dataset_adapter import find_csv, load_samples
from app.schemas import CurrentState, DatasetInfo, StreamStatus


router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "industrial-monitor",
    }


@router.get("/dataset", response_model=DatasetInfo)
def dataset_info():
    _, meta = load_samples(find_csv())
    return meta


@router.get("/state", response_model=CurrentState | None)
def current_state():
    from app.main import replay

    if not replay.history:
        return None

    item = replay.history[-1]

    return CurrentState(
        machine_id=1,
        machine_name="Máquina 01",
        state=item["state"],
        confidence=item["confidence"],
        predicted_class=item["predicted_class"],
        model_version=item["model_version"],
        source=item.get("source", "—"),
        signal_value=float(item.get("signal_value", 0.0)),
        rms=float(item.get("rms", 0.0)),
        timestamp=item["timestamp"],
        alert=item.get("alert"),
        severity=item.get("severity"),
    )


@router.get("/history")
def history(limit: int = 120):
    from app.main import replay

    return replay.history[-max(1, min(limit, 2000)):]


@router.get("/status", response_model=StreamStatus)
def status():
    from app.main import replay

    return replay.current_status()


@router.post("/replay/start")
async def start_replay():
    from app.main import replay

    if replay.running:
        return {"message": "Replay já está em execução."}

    asyncio.create_task(replay.run())

    return {"message": "Replay iniciado."}


@router.post("/replay/stop")
def stop_replay():
    from app.main import replay

    replay.stop()

    return {"message": "Replay interrompido."}


@router.post("/replay/reset")
def reset_replay():
    from app.main import replay

    replay.reset()

    return {"message": "Replay reiniciado."}


@router.get("/stream")
async def stream():
    from app.main import replay

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()

        async def subscriber(item: dict):
            await queue.put(item)

        replay.subscribe(subscriber)

        try:
            snapshot = replay.history[-1] if replay.history else {
                "machine_id": 1,
                "state": "AGUARDANDO",
                "predicted_class": "AGUARDANDO",
                "confidence": 0.0,
                "model_version": "—",
                "source": "—",
                "signal_value": 0.0,
                "rms": 0.0,
                "alert": None,
                "severity": None,
                "timestamp": datetime.now(timezone.utc),
            }

            yield f"data: {json.dumps(snapshot, default=str)}\n\n"

            while True:
                item = await queue.get()
                yield f"data: {json.dumps(item, default=str)}\n\n"

        finally:
            replay.unsubscribe(subscriber)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )