import subprocess
import sys
import tempfile
import os
from tools.registry import registry


@registry.register(
    name="execute_python",
    description="Execute a short Python code snippet and return its stdout/stderr. Use print() to output results.",
    allowed_agents=["code_specialist"],
)
def execute_python(code: str, timeout_seconds: int = 10) -> dict:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Execution timed out after {timeout_seconds} seconds.",
            "exit_code": -1,
        }
    finally:
        os.unlink(temp_path)