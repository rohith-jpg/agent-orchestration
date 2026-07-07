import time
import functools
from typing import Callable, Any
from pydantic import BaseModel


class ToolCallLog(BaseModel):
    tool_name: str
    inputs: dict
    output: Any = None
    latency_ms: float = 0.0
    success: bool = True
    error: str | None = None


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}
        self.call_log: list[ToolCallLog] = []

    def register(self, name: str, description: str, allowed_agents: list[str] | None = None):
        def decorator(func: Callable):
            self._tools[name] = {
                "func": func,
                "description": description,
                "allowed_agents": allowed_agents or ["*"],
            }
            return func
        return decorator

    def get(self, name: str) -> Callable:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered. Known: {list(self._tools)}")
        return self._tools[name]["func"]

    def call(self, name: str, **kwargs) -> Any:
        func = self.get(name)
        start = time.perf_counter()
        log = ToolCallLog(tool_name=name, inputs=kwargs)
        try:
            result = func(**kwargs)
            log.output = result
            return result
        except Exception as e:
            log.success = False
            log.error = str(e)
            raise
        finally:
            log.latency_ms = (time.perf_counter() - start) * 1000
            self.call_log.append(log)


registry = ToolRegistry()