"""In-memory pub/sub event manager for SSE staff notifications.

Each connected staff client subscribes to a queue filtered by prop_id.
When a guest event occurs (message or service request), all connected
staff for that property receive the event via SSE.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from asyncio import Queue
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StayEventManager:
    """Singleton event bus for in-stay real-time notifications."""

    _instance: StayEventManager | None = None
    _init_lock = asyncio.Lock()
    _sync_lock = threading.Lock()

    def __init__(self) -> None:
        # Map: prop_id → set of queues
        self._subscribers: dict[int, set[Queue]] = {}
        self._lock = asyncio.Lock()
        # Store the server's main event loop for thread-safe publishing
        try:
            self._main_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._main_loop = asyncio.get_event_loop()

    @classmethod
    async def instance(cls) -> StayEventManager:
        if cls._instance is None:
            async with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def instance_sync(cls) -> StayEventManager:
        """Get or create the singleton from a synchronous context (thread-safe)."""
        if cls._instance is None:
            with cls._sync_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def subscribe(self, prop_id: int) -> Queue:
        """Register a new subscriber for the given property.

        Returns an asyncio.Queue that will receive event dicts.
        Also captures the server's main event loop for thread-safe publishing.
        """
        # Capture the real main loop (always correct in an async context)
        try:
            self._main_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        q: Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            if prop_id not in self._subscribers:
                self._subscribers[prop_id] = set()
            self._subscribers[prop_id].add(q)
        logger.debug("SSE subscriber added for prop_id=%s (total=%s)", prop_id, len(self._subscribers.get(prop_id, set())))
        return q

    async def unsubscribe(self, prop_id: int, q: Queue) -> None:
        """Remove a subscriber queue."""
        async with self._lock:
            subs = self._subscribers.get(prop_id, set())
            subs.discard(q)
            if not subs:
                self._subscribers.pop(prop_id, None)
        logger.debug("SSE subscriber removed for prop_id=%s", prop_id)

    async def publish(self, prop_id: int, event_type: str, data: dict) -> None:
        """Push an event to all subscribers for the given property."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": _now_iso(),
        }
        payload = json.dumps(event, default=str)
        async with self._lock:
            subs = list(self._subscribers.get(prop_id, set()))
        dead: list[Queue] = []
        for q in subs:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
                logger.warning("SSE queue full for prop_id=%s, dropping subscriber", prop_id)
        # Clean up dead queues
        if dead:
            async with self._lock:
                remaining = self._subscribers.get(prop_id, set())
                for d in dead:
                    remaining.discard(d)
                if not remaining:
                    self._subscribers.pop(prop_id, None)

    def publish_threadsafe(self, prop_id: int, event_type: str, data: dict) -> None:
        """Thread-safe publish — schedules on the main event loop."""
        try:
            self._main_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.publish(prop_id, event_type, data))
            )
        except Exception:
            logger.debug("Failed to schedule SSE publish (loop may be stopped)")
