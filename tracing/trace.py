import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

TRACE_DIR = Path("traces")


class Trace:
    def __init__(self, task: str):
        self.trace_id = str(uuid.uuid4())[:8]
        self.task = task
        self.started_at = time.time()
        self.events: list[dict] = []

    def log(self, event_type: str, **details) -> None:
        self.events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - self.started_at, 2),
            "event_type": event_type,
            **details,
        })

    def save(self) -> Path:
        TRACE_DIR.mkdir(exist_ok=True)
        path = TRACE_DIR / f"trace_{self.trace_id}.json"
        with open(path, "w") as f:
            json.dump({
                "trace_id": self.trace_id,
                "task": self.task,
                "started_at": datetime.fromtimestamp(self.started_at, tz=timezone.utc).isoformat(),
                "total_duration_seconds": round(time.time() - self.started_at, 2),
                "events": self.events,
            }, f, indent=2)
        return path

    def print_summary(self) -> None:
        from rich import print as rprint
        rprint(f"\n[bold blue]Trace {self.trace_id}[/bold blue] -- {len(self.events)} events, "
               f"{round(time.time() - self.started_at, 2)}s total")
        for e in self.events:
            rprint(f"  [{e['elapsed_seconds']:>6.2f}s] [cyan]{e['event_type']}[/cyan] "
                   f"{ {k: v for k, v in e.items() if k not in ('timestamp', 'elapsed_seconds', 'event_type')} }")