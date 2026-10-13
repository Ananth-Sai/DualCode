import difflib
from typing import Callable, Any

import config
from tasks.schemas import Task, WriterOutput, CritiqueResult
from agents.writer import write_code as default_write_code
from agents.critic import review_code as default_review_code


def calculate_similarity(code_a: str, code_b: str) -> float:
    """Calculate the similarity ratio between two code strings using difflib."""
    return difflib.SequenceMatcher(None, code_a, code_b).ratio()


def run_loop(
    task: Task,
    max_rounds: int = config.MAX_ROUNDS,
    stall_threshold: float = config.STALL_THRESHOLD,
    writer_fn: Callable[..., WriterOutput] = default_write_code,
    critic_fn: Callable[..., CritiqueResult] = default_review_code,
) -> dict[str, Any]:
    """Execute the iterative Writer/Critic loop with deterministic stop conditions.

    Zero LLM calls are made in this function directly; all control decisions
    (approval, stall detection, round ceiling) are deterministic pure Python.

    Returns:
        dict containing:
            - final_code: str
            - rounds_used: int
            - verdict_history: list[dict]
            - stopped_reason: "approved" | "stalled" | "max_rounds"
    """
    verdict_history: list[dict[str, Any]] = []
    current_code = ""
    critique: CritiqueResult | None = None

    for round_num in range(1, max_rounds + 1):
        if round_num == 1:
            # Round 1: Fresh generation from task spec
            writer_output = writer_fn(task)
            current_code = writer_output.code
        else:
            # Round 2+: Targeted revision with previous code and critic's issues
            previous_code = current_code
            writer_output = writer_fn(
                task,
                previous_code=previous_code,
                critique=critique,
                round_number=round_num,
            )
            current_code = writer_output.code

            # Stall Detection: check if the revision made virtually no changes
            similarity = calculate_similarity(previous_code, current_code)
            if similarity >= stall_threshold:
                return {
                    "final_code": current_code,
                    "rounds_used": round_num,
                    "verdict_history": verdict_history,
                    "stopped_reason": "stalled",
                }

        # Critic evaluates the current candidate code
        critique = critic_fn(task, current_code)
        verdict_history.append(
            {
                "round": round_num,
                "verdict": critique.verdict,
                "issues_count": len(critique.issues),
                "summary": critique.summary,
            }
        )

        # Stop condition 1: Approved by Critic
        if critique.verdict == "APPROVE":
            return {
                "final_code": current_code,
                "rounds_used": round_num,
                "verdict_history": verdict_history,
                "stopped_reason": "approved",
            }

        # Stop condition 2: Max rounds reached without approval
        if round_num >= max_rounds:
            return {
                "final_code": current_code,
                "rounds_used": round_num,
                "verdict_history": verdict_history,
                "stopped_reason": "max_rounds",
            }

    return {
        "final_code": current_code,
        "rounds_used": max_rounds,
        "verdict_history": verdict_history,
        "stopped_reason": "max_rounds",
    }
