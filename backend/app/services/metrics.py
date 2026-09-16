from __future__ import annotations

from app.config import METRIC_MAX_GAP_SECONDS
from app.database.db import list_inferences, list_machines


def calculate_machine_metrics(machine: dict) -> dict:
    rows = list_inferences(machine["id"])

    operating_seconds = 0.0
    downtime_seconds = 0.0
    failure_count = 0
    previous_failure = False

    for index, row in enumerate(rows):
        failure = row.state == "FALHA" or row.severity == "CRITICAL"
        
        if failure and not previous_failure:
            failure_count += 1

        previous_failure = failure

        if index + 1 >= len(rows):
            continue

        delta = (rows[index + 1].timestamp - row.timestamp).total_seconds()

        if delta <= 0 or delta > METRIC_MAX_GAP_SECONDS:
            continue

        if row.state in {"DESLIGADO", "FALHA"}:
            downtime_seconds += delta
        else:
            operating_seconds += delta

    monitored_seconds = operating_seconds + downtime_seconds

    availability = (
        operating_seconds / monitored_seconds
        if monitored_seconds > 0 else None
    )

    total_count = machine["total_count"]
    good_count = machine["good_count"]
    ideal_cycle = machine["ideal_cycle_time_seconds"]

    performance = (
        min(1.0, (ideal_cycle * total_count) / operating_seconds)
        if ideal_cycle and total_count > 0 and operating_seconds > 0 else None
    )

    quality = (
        min(1.0, good_count / total_count)
        if total_count > 0 else None
    )

    oee = (
        availability * performance * quality
        if availability is not None
        and performance is not None
        and quality is not None
        else None
    )

    mtbf_hours = (
        (operating_seconds / failure_count) / 3600
        if failure_count > 0 else None
    )

    return {
        "machine_id": machine["id"],
        "availability": availability * 100 if availability is not None else None,
        "performance": performance * 100 if performance is not None else None,
        "quality": quality * 100 if quality is not None else None,
        "oee": oee * 100 if oee is not None else None,
        "mtbf_hours": mtbf_hours,
        "operating_hours": operating_seconds / 3600,
        "downtime_hours": downtime_seconds / 3600,
        "failure_count": failure_count,
        "total_count": total_count,
        "good_count": good_count,
        "ideal_cycle_time_seconds": ideal_cycle,
    }


def calculate_overview_metrics() -> dict:
    machines = list_machines()
    metrics = [calculate_machine_metrics(machine) for machine in machines]

    oee_values = [item["oee"] for item in metrics if item["oee"] is not None]
    operating_hours = sum(item["operating_hours"] for item in metrics)
    failures = sum(item["failure_count"] for item in metrics)

    return {
        "oee": sum(oee_values) / len(oee_values) if oee_values else None,
        "mtbf_hours": operating_hours / failures if failures else None,
        "machine_count": len(machines),
        "failure_count": failures,
    }