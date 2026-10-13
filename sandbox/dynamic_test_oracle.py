import ast
import re
import time
from google import genai
from google.genai import types

import config
from tasks.schemas import Task

_client: genai.Client | None = None


def get_client() -> genai.Client:
    """Lazily initialize and return the Gemini API client."""
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please provide it in your .env file or environment."
            )
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def extract_python_code(raw_text: str) -> str:
    """Extract clean Python code from markdown code blocks or raw text."""
    pattern = r"```(?:python)?\s*\n(.*?)```"
    match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw_text.strip()


def synthesize_test_suite(task: Task, max_retries: int = 2) -> str | None:
    """Generate an independent, rigorous pytest suite (4-6 assertions) for an arbitrary Task specification.
    
    Returns:
        str: Executable Python test string if synthesis succeeded.
        None: If test generation failed across all candidate models (avoids silent false-pass).
    """
    client = get_client()
    prompt = f"""You are an elite QA / Test Automation Engineer.
Generate an independent, rigorous pytest test suite (4 to 6 focused test functions) to thoroughly verify a Python implementation of the following specification.

Specification:
{task.spec}

Target Function Signature:
{task.function_signature}

Requirements:
1. Write 4 to 6 separate test functions named `def test_<description>():`.
2. Cover:
   - Happy path / standard valid inputs
   - Edge case boundaries (e.g. empty values, 0, min/max lengths)
   - Negative / invalid formats that must return False or raise exceptions as specified.
3. Use standard `assert` statements.
4. If the specification indicates returning False, None, or a default value on invalid/malformed inputs, assert the return value (e.g. `assert func(invalid) is False`). Only use `pytest.raises(...)` if the specification explicitly mandates raising an exception.
5. CRITICAL: Do NOT redefine, re-declare, or import the target function. Assume the function is ALREADY defined and available in the global namespace.
6. Output ONLY executable Python code containing the test functions. No markdown commentary.
"""

    candidate_models = [config.CRITIC_MODEL] + [
        m for m in config.FALLBACK_MODELS if m != config.CRITIC_MODEL
    ]

    for model_name in candidate_models:
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                    ),
                )
                raw_code = response.text or ""
                clean_tests = extract_python_code(raw_code)

                # Validate syntactic correctness of synthesized tests
                ast.parse(clean_tests)
                if "def test_" in clean_tests:
                    return clean_tests

            except Exception:
                time.sleep(0.5)

    # Return None instead of a dummy pass assertion so failures are reported transparently
    return None
