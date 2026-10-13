import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import config
from tasks.schemas import Task


def run_hidden_tests(
    code: str,
    task: Task,
    timeout_seconds: int = config.TEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Execute generated code against the task's hidden pytest suite in a sandboxed subprocess.

    This function represents GROUND TRUTH:
    Pass/fail is determined by real pytest execution, independent of the Critic's assessment.

    Returns:
        dict containing:
            - passed: bool
            - pass_count: int
            - fail_count: int
            - output: str
    """
    # Combine the candidate function code and the hidden pytest assertions
    test_file_content = f"""# Auto-generated submission test file
import sys

{code}

# --- Hidden Ground Truth Tests ---
{task.hidden_tests}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file_path = Path(temp_dir) / "test_submission.py"
        test_file_path.write_text(test_file_content, encoding="utf-8")

        # Prepare isolated execution environment (clean subprocess, no secrets passed)
        env = os.environ.copy()
        # Remove API keys from subprocess environment for safety
        env.pop("GEMINI_API_KEY", None)

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_file_path),
            "-q",
            "--tb=short",
            "--no-header",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
            )

            stdout = result.stdout or ""
            stderr = result.stderr or ""
            combined_output = (stdout + "\n" + stderr).strip()

            passed = result.returncode == 0

            # Extract pass/fail counts using regex from pytest output
            pass_match = re.search(r"(\d+)\s+passed", combined_output)
            fail_match = re.search(r"(\d+)\s+failed", combined_output)
            error_match = re.search(r"(\d+)\s+error", combined_output)

            pass_count = int(pass_match.group(1)) if pass_match else (1 if passed else 0)
            fail_count = 0
            if fail_match:
                fail_count += int(fail_match.group(1))
            if error_match:
                fail_count += int(error_match.group(1))
            if not passed and fail_count == 0:
                fail_count = 1

            return {
                "passed": passed,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "output": combined_output,
            }

        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "pass_count": 0,
                "fail_count": 1,
                "output": f"Execution timed out after {timeout_seconds} seconds.",
            }
        except Exception as exc:
            return {
                "passed": False,
                "pass_count": 0,
                "fail_count": 1,
                "output": f"Subprocess execution error: {exc}",
            }
