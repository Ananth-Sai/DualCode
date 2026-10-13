import time
from google import genai
from google.genai import types

import config
from tasks.schemas import Task, CritiqueResult

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


def build_critic_prompt(task: Task, code: str) -> str:
    """Construct a rigorous prompt demanding evaluation across all 5 rubric criteria."""
    return f"""You are a Staff Software Engineer conducting an uncompromising, rigorous code review.

Task Specification:
{task.spec}

Required Function Signature:
{task.function_signature}

Candidate Implementation to Review:
```python
{code}
```

Evaluation Rubric:
Analyze the code against each of the following 5 dimensions:
1. CORRECTNESS: Does the code strictly produce the correct output for all valid inputs? Are there off-by-one errors, incorrect return types, or logic bugs?
2. EDGE CASES: Does the code handle boundary inputs (e.g., empty strings/lists, single items, negative numbers, unusual characters, zero values)?
3. SECURITY: Does the code avoid memory exhaustion, dangerous constructs, or unhandled exceptions?
4. READABILITY: Is the code clean, idiomatic Python with proper naming and structure?
5. PERFORMANCE: Is the time and space complexity optimal for the problem?

Verdict Guidelines:
- If there are ANY bugs, missing edge cases, logic flaws, or signature mismatches:
  You MUST set verdict to "REVISE".
  List every specific flaw in the 'issues' field with category, severity ("critical" or "minor"), explanation, and concrete suggestion.
- You may ONLY set verdict to "APPROVE" if the solution is completely correct, fully satisfies the signature and specification, and handles all edge cases with zero critical issues.
- Be vigilant: do not rubber-stamp flawed or incomplete implementations.
"""


def _review_with_retry(prompt: str, max_retries: int = 2) -> CritiqueResult:
    """Execute structured review call with model failover and retries."""
    client = get_client()
    candidate_models = [config.CRITIC_MODEL] + [
        m for m in config.FALLBACK_MODELS if m != config.CRITIC_MODEL
    ]

    last_exception = None
    for model_name in candidate_models:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=CritiqueResult,
                        temperature=config.CRITIC_TEMPERATURE,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )
                if response.parsed is not None and isinstance(response.parsed, CritiqueResult):
                    return response.parsed
                if response.text:
                    return CritiqueResult.model_validate_json(response.text)
                raise ValueError("Empty response received from Critic model.")
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    time.sleep(1.5 * attempt)
        # If this model failed, fall through to the next candidate model

    if last_exception:
        raise last_exception
    raise RuntimeError("Failed to obtain CritiqueResult after all models exhausted.")


def review_code(task: Task, code: str) -> CritiqueResult:
    """Review candidate code against the task specification and return structured CritiqueResult."""
    prompt = build_critic_prompt(task, code)
    return _review_with_retry(prompt)
