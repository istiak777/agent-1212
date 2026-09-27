import json
from collections import deque
from pathlib import Path


class PersistentSessionManager:
    """Persist a browser session state for logged-in or saved work contexts."""

    def __init__(self, session_name, storage_dir=".sessions"):
        self.session_name = session_name
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.storage_dir / f"{session_name}.json"

    def save(self, state):
        self.file_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return state

    def get(self, key=None, default=None):
        if not self.file_path.exists():
            return default
        data = json.loads(self.file_path.read_text(encoding="utf-8") or "{}")
        if key is None:
            return data
        return data.get(key, default)

    def clear(self):
        if self.file_path.exists():
            self.file_path.unlink()


class CommandQueue:
    """Simple FIFO queue for approved personal workflows."""

    def __init__(self):
        self._queue = deque()

    def enqueue(self, command):
        self._queue.append(command)
        return command

    def dequeue(self):
        if not self._queue:
            raise IndexError("Queue is empty")
        return self._queue.popleft()

    def empty(self):
        return len(self._queue) == 0

    def size(self):
        return len(self._queue)
