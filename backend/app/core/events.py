import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, List, Optional
import uuid


class InvestigationEvent:
    def __init__(
        self,
        investigation_id: str,
        event_type: str,
        data: dict,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.investigation_id = investigation_id
        self.event_type = event_type
        self.data = data
        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_sse(self) -> str:
        """Format as Server-Sent Event string."""
        payload = {
            "id": self.event_id,
            "investigation_id": self.investigation_id,
            "event_type": self.event_type,
            "type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }
        return f"id: {self.event_id}\ndata: {json.dumps(payload)}\n\n"


class EventBus:
    """In-memory PubSub event bus for real-time investigation updates."""

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, investigation_id: str) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            if investigation_id not in self._subscribers:
                self._subscribers[investigation_id] = []
            self._subscribers[investigation_id].append(queue)

        try:
            # Yield initial connection event
            initial_event = InvestigationEvent(
                investigation_id=investigation_id,
                event_type="connected",
                data={"message": "Stream connected successfully"},
            )
            yield initial_event.to_sse()

            while True:
                # Wait for next event or keepalive timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield event.to_sse()
                except asyncio.TimeoutError:
                    # Send comment keep-alive ping
                    yield ": ping\n\n"
        finally:
            async with self._lock:
                if investigation_id in self._subscribers:
                    if queue in self._subscribers[investigation_id]:
                        self._subscribers[investigation_id].remove(queue)
                    if not self._subscribers[investigation_id]:
                        del self._subscribers[investigation_id]

    async def publish(self, event: InvestigationEvent) -> None:
        async with self._lock:
            queues = self._subscribers.get(event.investigation_id, [])
            for queue in queues:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass  # drop if slow consumer


event_bus = EventBus()
