from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from fastapi.responses import StreamingResponse

from app.config import machine_csv_path
from app.database.db import create_machine, get_machine, list_inferences, list_machines, update_machine_production

from app.schemas import CurrentState, DatasetInfo, MachineCreate, MachineInfo, MachineMetrics, OverviewResponse, ProductionUpdate, StreamStatus
from app.services.metrics import calculate_machine_metrics, calculate_overview_metrics


router = APIRouter(prefix="/api")


def machine_info(machine: dict) -> dict:
    return {
        **machine,
        "dataset_file": machine_csv_path(machine["id"]).name,
    }

def inference_to_dict(item) -> dict:
    if isinstance(item, dict):
        return item
    return {
        "machine_id": item.machine_id,
        "timestamp": item.timestamp,
        "predicted_class": item.predicted_class,
        "confidence": item.confidence,
        "model_version": item.model_version,
        "source": item.source,
        "signal_value": item.signal_value,
        "rms": item.rms,
        "state": item.state,
        "alert": item.alert,
        "severity": item.severity,
        "rpm_raw": item.rpm_raw,
        "rpm_filtered": item.rpm_filtered,
        "rpm_pulses": item.rpm_pulses,
        "rpm_pulse_hz": item.rpm_pulse_hz,
        "temperature_c": item.temperature_c,
        "ntc_raw": item.ntc_raw,
        "ntc_voltage": item.ntc_voltage,
        "ntc_resistance": item.ntc_resistance,
    }

@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "industrial-monitor",
    }

@router.get("/dataset", response_model=DatasetInfo)
def dataset_info():
    from app.main import replay
    return replay.meta

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

@router.get("/machines", response_model=list[MachineInfo])
def machines():
    return [machine_info(machine) for machine in list_machines()]


@router.post("/machines", response_model=MachineInfo, status_code=201)
def register_machine(payload: MachineCreate):
    machine = create_machine(
        payload.name,
        payload.ideal_cycle_time_seconds,
        payload.total_count,
        payload.good_count,
    )

    path = machine_csv_path(machine["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return machine_info(machine)

@router.get("/machines/{machine_id}", response_model=MachineInfo)
def machine_detail(machine_id: int):
    machine = get_machine(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")

    return machine_info(machine)

@router.get("/machines/{machine_id}/state", response_model=CurrentState | None)
def machine_state(machine_id: int):
    machine = get_machine(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")

    from app.main import replay
    item = replay.latest(machine_id)
    if item is None:
        rows = list_inferences(machine_id, 1)
        item = rows[-1] if rows else None
    if item is None:
        return None
    item = inference_to_dict(item)
    return CurrentState(
        machine_id=machine_id,
        machine_name=machine["name"],
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
        rpm_raw=item.get("rpm_raw"),
        rpm_filtered=item.get("rpm_filtered"),
        rpm_pulses=item.get("rpm_pulses"),
        rpm_pulse_hz=item.get("rpm_pulse_hz"),
        temperature_c=item.get("temperature_c"),
        ntc_raw=item.get("ntc_raw"),
        ntc_voltage=item.get("ntc_voltage"),
        ntc_resistance=item.get("ntc_resistance"),
    )


@router.get("/machines/{machine_id}/history")
def machine_history(machine_id: int, limit: int = 120):
    from app.main import replay
    if get_machine(machine_id) is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")

    limit = max(1, min(limit, 2000))
    items = replay.history_for(machine_id, limit)
    if items:
        return items
    rows = list_inferences(machine_id, limit)
    return [inference_to_dict(row) for row in rows]


@router.get("/machines/{machine_id}/metrics", response_model=MachineMetrics)
def machine_metrics(machine_id: int):
    machine = get_machine(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")

    return calculate_machine_metrics(machine)

@router.put("/machines/{machine_id}/production", response_model=MachineMetrics)
def update_production(machine_id: int, payload: ProductionUpdate):
    machine = update_machine_production(
        machine_id,
        payload.total_count,
        payload.good_count,
        payload.ideal_cycle_time_seconds,
    )

    if machine is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")

    return calculate_machine_metrics(machine)


@router.get("/machines/{machine_id}/status", response_model=StreamStatus)
def machine_status(machine_id: int):
    from app.main import replay
    if get_machine(machine_id) is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")

    return replay.current_status(machine_id)


@router.post("/machines/{machine_id}/replay/start")
async def start_machine_replay(machine_id: int):
    from app.main import replay
    if get_machine(machine_id) is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")

    asyncio.create_task(replay.run(machine_id))
    return {"message": "Replay iniciado."}

@router.post("/machines/{machine_id}/replay/stop")
def stop_machine_replay(machine_id: int):
    from app.main import replay
    if get_machine(machine_id) is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")

    replay.stop(machine_id)
    return {"message": "Replay interrompido."}


@router.post("/machines/{machine_id}/replay/reset")
def reset_machine_replay(machine_id: int):
    from app.main import replay
    if get_machine(machine_id) is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")
    replay.reset(machine_id)
    return {"message": "Replay reiniciado."}


@router.get("/machines/{machine_id}/stream")
async def machine_stream(machine_id: int):
    from app.main import replay

    if get_machine(machine_id) is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()

        async def subscriber(item: dict):
            if item.get("machine_id") == machine_id:
                await queue.put(item)

        replay.subscribe(subscriber)

        try:
            latest = replay.latest(machine_id)

            if latest is not None:
                yield f"data: {json.dumps(latest, default=str)}\n\n"

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


@router.get("/overview", response_model=OverviewResponse)
def overview():
    machines = list_machines()
    summaries = []
    for machine in machines:
        state = machine_state(machine["id"])
        summaries.append({
            "machine": machine_info(machine),
            "state": state,
            "metrics": calculate_machine_metrics(machine),
        })
    metrics = calculate_overview_metrics()
    metrics["operating_count"] = sum(
        1 for item in summaries
        if item["state"] and item["state"].state == "OPERANDO"
    )
    metrics["alert_count"] = sum(
        1 for item in summaries
        if item["state"] and item["state"].alert
    )
    return {
        "metrics": metrics,
        "machines": summaries,
    }