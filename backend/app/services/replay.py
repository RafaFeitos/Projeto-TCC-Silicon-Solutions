from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import asdict
from typing import Awaitable, Callable

from app.config import REPLAY_DELAY_SECONDS, WINDOW_SIZE
from app.inference.dataset_adapter import find_csv, infer_window, load_samples


class ReplayEngine:
    def __init__(self) -> None:
        self.samples, self.meta = load_samples(find_csv())
        self.cursor = 0
        self.running = False
        self.history: list[dict] = []
        self._subscribers: set[Callable[[dict], Awaitable[None]]] = set()

    def subscribe(self, callback):
        self._subscribers.add(callback)

    def unsubscribe(self, callback):
        self._subscribers.discard(callback)

    def reset(self):
        self.cursor = 0
        self.running = False
        self.history.clear()

    def current_status(self) -> dict:
        return {
            "running": self.running,
            "cursor": self.cursor,
            "total": len(self.samples),
        }

    async def _emit(self, item: dict) -> None:
        for callback in list(self._subscribers):
            try:
                await callback(item)
            except Exception:
                self._subscribers.discard(callback)

    async def run(self) -> None:
        if self.running:
            return
        self.running = True
        try:
            window: deque = deque(maxlen=WINDOW_SIZE)
            while self.cursor < len(self.samples) and self.running:
                sample = self.samples[self.cursor]
                window.append(sample)
                result = infer_window(list(window))
                result["machine_id"] = 1
                self.history.append(result)
                if len(self.history) > 2000:
                    self.history = self.history[-2000:]
                self.cursor += 1
                await self._emit(result)
                await asyncio.sleep(REPLAY_DELAY_SECONDS)
        finally:
            self.running = False

    def stop(self):
        self.running = False