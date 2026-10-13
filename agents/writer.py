import re
import time
from google import genai
from google.genai import types

import config
from tasks.schemas import Task, WriterOutput, CritiqueResult

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


def build_writer_prompt(
    task: Task,
    previous_code: str | None = None,
    critique: CritiqueResult | None = None,
) -> str:
    """Construct prompt for Round 1 (initial write) or Round 2+ (targeted revision)."""
    if previous_code is None or critique is None:
        return f"""You are an expert Python engineer. Write a clean, robust, and correct implementation of the specified function.

Task Specification:
{task.spec}

Required Function Signature:
{task.function_signature}

Instructions:
1. Return ONLY the Python code implementing this function.
2. Include standard library imports at the top if needed.
3. Handle edge cases mentioned in the specification.
4. Do NOT include markdown explanations, usage examples, or extra prose. Output code only.
"""

    # Round 2+ prompt with critique feedback
    issues_text = ""
    for idx, issue in enumerate(critique.issues, 1):
        issues_text += (
            f"{idx}. [{issue.category.upper()} - {issue.severity.upper()}]\n"
            f"   Explanation: {issue.explanation}\n"
            f"   Suggestion: {issue.suggestion}\n"
        )
    if not issues_text:
        issues_text = "Review requested revision without itemized points."

    return f"""You are an expert Python engineer revising your code based on a senior code review.

Task Specification:
{task.spec}

Required Function Signature:
{task.function_signature}

Your Previous Code:
```python
{previous_code}
```

Review Summary:
{critique.summary}

Identified Issues:
{issues_text}

Instructions:
1. Address EVERY identified issue while strictly adhering to the original specification.
2. Return ONLY the complete, revised Python code.
3. Do NOT include markdown explanations, apologies, or commentary. Output code only.
"""


def _generate_with_retry(prompt: str, max_retries: int = 2) -> str:
    """Call Gemini API with automatic model failover and retries on transient errors."""
    client = get_client()
    candidate_models = [config.WRITER_MODEL] + [
        m for m in config.FALLBACK_MODELS if m != config.WRITER_MODEL
    ]

    last_exception = None
    for model_name in candidate_models:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=config.WRITER_TEMPERATURE,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )
                return response.text or ""
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    time.sleep(1.5 * attempt)
        # If this model failed, fall through to the next candidate model

    if last_exception:
        raise last_exception
    return ""


def write_code(
    task: Task,
    previous_code: str | None = None,
    critique: CritiqueResult | None = None,
    round_number: int = 1,
) -> WriterOutput:
    """Generate or revise code for a given task using the Writer LLM with failover."""
    prompt = build_writer_prompt(task, previous_code=previous_code, critique=critique)
    raw_text = _generate_with_retry(prompt)
    clean_code = extract_python_code(raw_text)
    return WriterOutput(code=clean_code, round_number=round_number)
