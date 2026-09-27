import json
from pathlib import Path


class WorkflowMemory:
    """Persist personal command patterns and preferences locally."""

    def __init__(self, path=".agent_memory.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _read(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            return {}

    def _write(self, payload):
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def record(self, command, action, result, notes=None):
        data = self._read()
        entry = {
            "command": command,
            "action": action,
            "result": result,
            "notes": notes or "",
        }
        history = data.setdefault("history", [])
        history.append(entry)
        data["preferences"] = data.get("preferences", {})
        data["preferences"].setdefault(action, {"count": 0, "commands": []})
        data["preferences"][action]["count"] += 1
        data["preferences"][action]["commands"].append(command)
        self._write(data)
        return entry

    def recent(self, limit=5):
        data = self._read()
        return list(reversed(data.get("history", [])))[-limit:]

    def suggest(self):
        data = self._read()
        preferences = data.get("preferences", {})
        return {
            action: meta.get("count", 0)
            for action, meta in sorted(preferences.items(), key=lambda item: item[1].get("count", 0), reverse=True)
        }
