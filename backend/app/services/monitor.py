from __future__ import annotations

from typing import Awaitable, Callable

from app.config import MONITOR_MODE
from app.services.machine_manager import (
    MachineManager,
)
from app.services.replay import ReplayEngine


Subscriber = Callable[
    [dict],
    Awaitable[None],
]


class MonitorEngine:
    def __init__(self) -> None:
        self._replay = ReplayEngine()
        self._machines = MachineManager()
        self._history: dict[
            int,
            list[dict],
        ] = {}
        self._subscribers: set[
            Subscriber
        ] = set()
        self._running: set[int] = set()
        self._cursor: dict[
            int,
            int,
        ] = {}
        self._mode: dict[
            int,
            str,
        ] = {}
        self._replay.subscribe(
            self._forward
        )

    @property
    def meta(self) -> dict:
        return self._replay.meta

    @property
    def cursor(self) -> int:
        return self._cursor.get(
            1,
            0,
        )

    @property
    def running(self) -> bool:
        return 1 in self._running

    @property
    def history(self) -> list[dict]:
        return self._history.setdefault(
            1,
            [],
        )

    def history_for(
        self,
        machine_id: int,
        limit: int | None = None,
    ) -> list[dict]:
        items = self._history.get(
            machine_id,
            [],
        )

        return (
            items[-limit:]
            if limit
            else items
        )

    def latest(
        self,
        machine_id: int,
    ) -> dict | None:
        items = self._history.get(
            machine_id,
            [],
        )

        return (
            items[-1]
            if items
            else None
        )

    def subscribe(
        self,
        callback: Subscriber,
    ) -> None:
        self._subscribers.add(
            callback
        )

    def unsubscribe(
        self,
        callback: Subscriber,
    ) -> None:
        self._subscribers.discard(
            callback
        )
    async def _forward(
        self,
        item: dict,
    ) -> None:
        machine_id = int(
            item.get(
                "machine_id",
                1,
            )
        )

        history = (
            self._history.setdefault(
                machine_id,
                [],
            )
        )

        history.append(item)

        if len(history) > 2000:
            self._history[
                machine_id
            ] = history[-2000:]
        self._cursor[
            machine_id
        ] = (
            self._cursor.get(
                machine_id,
                0,
            )
            + 1
        )
        for callback in list(
            self._subscribers
        ):
            try:
                await callback(item)
            except Exception:
                self._subscribers.discard(
                    callback
                )

    def _resolve_mode(
        self,
        machine_id: int,
    ) -> str:
        mode = (
            MONITOR_MODE
            .strip()
            .lower()
        )
        if mode == "replay":
            return "replay"
        if mode == "serial":
            return "serial"
        if mode == "auto":
            return (
                "serial"
                if self._machines.serial_available(
                    machine_id
                )
                else "replay"
            )
        raise RuntimeError(
            "MONITOR_MODE deve ser "
            "replay, serial ou auto."
        )

    async def run(
        self,
        machine_id: int = 1,
    ) -> None:
        if machine_id in self._running:
            return
        mode = self._resolve_mode(
            machine_id
        )
        self._mode[
            machine_id
        ] = mode
        self._running.add(
            machine_id
        )
        try:
            if mode == "serial":
                await self._machines.run(
                    machine_id,
                    self._forward,
                )
            else:
                await self._replay.run(
                    machine_id
                )
        finally:
            self._running.discard(
                machine_id
            )

    def stop(
        self,
        machine_id: int = 1,
    ) -> None:
        self._machines.stop(
            machine_id
        )
        self._replay.stop(
            machine_id
        )
        self._running.discard(
            machine_id
        )

    def reset(
        self,
        machine_id: int = 1,
    ) -> None:
        self.stop(machine_id)
        self._machines.reset(
            machine_id
        )
        self._replay.reset(
            machine_id
        )
        self._history[
            machine_id
        ] = []
        self._cursor[
            machine_id
        ] = 0
        self._mode.pop(
            machine_id,
            None,
        )

    def current_status(
        self,
        machine_id: int = 1,
    ) -> dict:
        mode = self._mode.get(
            machine_id,
            "replay",
        )
        if mode == "serial":
            serial_status = (
                self._machines.status(
                    machine_id
                )
            )
            return {
                "running":
                    machine_id
                    in self._running
                    and serial_status[
                        "running"
                    ],
                "cursor":
                    self._cursor.get(
                        machine_id,
                        0,
                    ),
                "total": 0,
            }
        replay_status = (
            self._replay.current_status(
                machine_id
            )
        )
        return {
            "running":
                machine_id
                in self._running,
            "cursor":
                replay_status[
                    "cursor"
                ],
            "total":
                replay_status[
                    "total"
                ],
        }

    def stop_all(self) -> None:
        self._machines.stop_all()

        for machine_id in list(
            self._running
        ):
            self._replay.stop(
                machine_id
            )
        self._running.clear()