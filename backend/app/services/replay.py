from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import asdict
from typing import Awaitable, Callable

from app.config import DEMO_DATASET_PATH, REPLAY_DELAY_SECONDS, WINDOW_SIZE
from app.inference.dataset_adapter import infer_window, load_samples


class ReplayEngine:
    def __init__(self) -> None:
        self.samples, self.meta = load_samples(DEMO_DATASET_PATH)
        self._cursor: dict[int, int] = {}
        self._running: set[int] = set()
        self._history: dict[int, list[dict]] = {}
        self._subscribers: set[Callable[[dict], Awaitable[None]]] = set()

    @property
    def cursor(self) -> int:
        return self._cursor.get(1, 0)

    @property
    def running(self) -> bool:
        return 1 in self._running

    @property
    def history(self) -> list[dict]:
        return self._history.setdefault(1, [])

    def history_for(self, machine_id: int, limit: int | None = None) -> list[dict]:
        items = self._history.get(machine_id, [])
        return items[-limit:] if limit else items

    def latest(self, machine_id: int) -> dict | None:
        items = self._history.get(machine_id, [])
        return items[-1] if items else None


    def subscribe(self, callback):
        self._subscribers.add(callback)

    def unsubscribe(self, callback):
        self._subscribers.discard(callback)

    def reset(self, machine_id: int = 1):
        self._cursor[machine_id] = 0
        self._running.discard(machine_id)
        self._history[machine_id] = []

    def current_status(self, machine_id: int = 1) -> dict:
        return {
            "running": machine_id in self._running,
            "cursor": self._cursor.get(machine_id, 0),
            "total": len(self.samples),
        }
    async def _emit(self, item: dict) -> None:
        for callback in list(self._subscribers):
            try:
                await callback(item)
            except Exception:
                self._subscribers.discard(callback)

    async def run(self, machine_id: int = 1) -> None:
        if machine_id in self._running:
            return
        
        self._running.add(machine_id)
        cursor = self._cursor.get(machine_id, 0)

        try:
            window: deque = deque(maxlen=WINDOW_SIZE)

            while cursor < len(self.samples) and machine_id in self._running:
                sample = self.samples[cursor]
                window.append(sample)

                result = infer_window(list(window))
                result["machine_id"] = machine_id

                history = self._history.setdefault(machine_id, [])
                history.append(result)

                if len(history) > 2000:
                    self._history[machine_id] = history[-2000:]

                cursor += 1
                self._cursor[machine_id] = cursor

                await self._emit(result)
                await asyncio.sleep(REPLAY_DELAY_SECONDS)

        finally:
            self._running.discard(machine_id)
            
    def stop(self, machine_id: int = 1):
        self._running.discard(machine_id)