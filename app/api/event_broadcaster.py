from typing import Dict, List, Any
import asyncio

class SongEventBroadcaster:
    """Very small in-memory pub/sub for song status updates (single-process)."""

    def __init__(self) -> None:
        # song_id -> list of queues
        self._listeners: Dict[int, List[asyncio.Queue]] = {}

    async def subscribe(self, song_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._listeners.setdefault(song_id, []).append(q)
        return q

    async def unsubscribe(self, song_id: int, queue: asyncio.Queue):
        listeners = self._listeners.get(song_id)
        if not listeners:
            return
        try:
            listeners.remove(queue)
        except ValueError:
            pass
        if not listeners:
            # clean up key
            self._listeners.pop(song_id, None)

    async def notify(self, song_id: int, payload: dict):
        for q in self._listeners.get(song_id, []):
            await q.put(payload)

broadcaster = SongEventBroadcaster() 