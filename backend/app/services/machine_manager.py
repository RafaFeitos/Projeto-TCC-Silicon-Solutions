from __future__ import annotations

from typing import Awaitable, Callable
from serial.tools import list_ports

from app.config import (
    SERIAL_BAUD,
    SERIAL_PORT,
    machine_csv_path,
)
from app.database.db import get_machine
from app.services.serial_ingest import (
    SerialIngestor,
)

EmitCallback = Callable[
    [dict],
    Awaitable[None],
]

class MachineManager:
    def __init__(self) -> None:
        self._workers: dict[
            int,
            SerialIngestor,
        ] = {}

    def resolve_port(
        self,
        machine_id: int,
    ) -> str:
        machine = get_machine(machine_id)
        if machine is None:
            raise RuntimeError(
                "Máquina não encontrada."
            )
        configured = (
            machine.get("serial_port")
            or SERIAL_PORT
            or "auto"
        ).strip()
        if configured.lower() != "auto":
            return configured
        available = [
            item.device
            for item
            in list_ports.comports()
        ]
        if len(available) == 1:
            return available[0]
        if not available:
            raise RuntimeError(
                "Nenhuma porta serial encontrada."
            )
        raise RuntimeError(
            "Mais de uma porta serial encontrada. "
            "Defina SERIAL_PORT no backend/.env."
        )
    
    def serial_available(
        self,
        machine_id: int,
    ) -> bool:
        try:
            self.resolve_port(machine_id)
            return True

        except RuntimeError:
            return False

    async def run(
        self,
        machine_id: int,
        emit: EmitCallback,
    ) -> None:
        current = self._workers.get(
            machine_id
        )

        if current and current.running:
            return

        machine = get_machine(machine_id)

        if machine is None:
            raise RuntimeError(
                "Máquina não encontrada."
            )

        worker = SerialIngestor(
            machine_id=machine_id,
            port=self.resolve_port(
                machine_id
            ),
            baud=int(
                machine.get("baud")
                or SERIAL_BAUD
            ),
            csv_path=machine_csv_path(
                machine_id
            ),
        )

        self._workers[
            machine_id
        ] = worker
        try:
            await worker.run(emit)
        finally:
            self._workers.pop(
                machine_id,
                None,
            )

    def stop(
        self,
        machine_id: int,
    ) -> None:
        worker = self._workers.get(
            machine_id
        )
        if worker:
            worker.stop()

    def reset(
        self,
        machine_id: int,
    ) -> None:
        self.stop(machine_id)
        self._workers.pop(
            machine_id,
            None,
        )

    def status(
        self,
        machine_id: int,
    ) -> dict:
        worker = self._workers.get(
            machine_id
        )
        if worker is None:
            return {
                "running": False,
                "cursor": 0,
                "total": 0,
            }

        return worker.status()
    
    def stop_all(self) -> None:
        for worker in list(
            self._workers.values()
        ):
            worker.stop()