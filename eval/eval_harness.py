import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config
from tasks.loader import load_task_bank
from tasks.schemas import Task
from agents.writer import write_code
from orchestrator import run_loop
from sandbox.test_runner import run_hidden_tests

DEFAULT_EVAL_DIR = Path(__file__).parent / "eval_results"


def run_evaluation(
    tasks: list[Task] | None = None,
    max_rounds: int = config.MAX_ROUNDS,
    output_dir: Path | str = DEFAULT_EVAL_DIR,
) -> dict[str, Any]:
    """Execute evaluation harness comparing Baseline vs Critic Loop across tasks.

    For every task:
    1. Baseline: Writer once -> Ground Truth pytest execution.
    2. Critic Loop: Full Orchestrated loop -> Ground Truth pytest execution.

    Aggregates pass rates, lift, false-approval rate, and stall rate,
    and persists a timestamped JSON scorecard report.
    """
    if tasks is None:
        tasks = load_task_bank()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    per_task_results: list[dict[str, Any]] = []

    total_tasks = len(tasks)
    baseline_passes = 0
    loop_passes = 0
    approved_rounds: list[int] = []
    false_approvals = 0
    false_rejections = 0
    stalls = 0

    print(f"\n=======================================================")
    print(f"Starting Evaluation Harness: {total_tasks} Tasks")
    print(f"=======================================================")

    for idx, task in enumerate(tasks, 1):
        print(f"\n[{idx}/{total_tasks}] Evaluating Task {task.id}: {task.title} ({task.difficulty})")

        # --- 1. Baseline Run (1-pass Writer, no Critic) ---
        t0_base = time.time()
        base_writer_out = write_code(task)
        base_test_res = run_hidden_tests(base_writer_out.code, task)
        base_latency = round(time.time() - t0_base, 2)
        base_passed = base_test_res["passed"]
        if base_passed:
            baseline_passes += 1

        print(f"  * Baseline: {'PASSED' if base_passed else 'FAILED'} ({base_latency}s)")

        # --- 2. Critic Loop Run (Iterative loop) ---
        t0_loop = time.time()
        loop_res = run_loop(task, max_rounds=max_rounds)
        loop_test_res = run_hidden_tests(loop_res["final_code"], task)
        loop_latency = round(time.time() - t0_loop, 2)
        loop_passed = loop_test_res["passed"]
        if loop_passed:
            loop_passes += 1

        stopped_reason = loop_res["stopped_reason"]
        rounds_used = loop_res["rounds_used"]

        # Track stops & false approvals (Rubber-stamping detector)
        is_false_approval = (stopped_reason == "approved") and (not loop_passed)
        if is_false_approval:
            false_approvals += 1

        # Track false rejections (Hyper-criticism detector: tests passed but Critic never approved)
        is_false_rejection = (stopped_reason != "approved") and loop_passed
        if is_false_rejection:
            false_rejections += 1

        if stopped_reason == "approved":
            approved_rounds.append(rounds_used)
        elif stopped_reason == "stalled":
            stalls += 1

        print(
            f"  * Critic Loop: {'PASSED' if loop_passed else 'FAILED'} "
            f"(Rounds: {rounds_used}, Reason: {stopped_reason}, Latency: {loop_latency}s)"
        )
        if is_false_approval:
            print(f"  [!] FALSE APPROVAL DETECTED: Critic approved, but hidden tests failed!")
        if is_false_rejection:
            print(f"  [!] FALSE REJECTION DETECTED: Tests passed, but Critic never approved ({stopped_reason})!")

        per_task_results.append(
            {
                "task_id": task.id,
                "title": task.title,
                "difficulty": task.difficulty,
                "baseline_passed": base_passed,
                "baseline_pass_count": base_test_res["pass_count"],
                "baseline_fail_count": base_test_res["fail_count"],
                "baseline_latency_sec": base_latency,
                "loop_passed": loop_passed,
                "loop_pass_count": loop_test_res["pass_count"],
                "loop_fail_count": loop_test_res["fail_count"],
                "loop_latency_sec": loop_latency,
                "rounds_used": rounds_used,
                "stopped_reason": stopped_reason,
                "false_approval": is_false_approval,
                "false_rejection": is_false_rejection,
                "verdict_history": loop_res["verdict_history"],
            }
        )

    # --- Compute Aggregate Scorecard Metrics ---
    baseline_pass_rate = round(baseline_passes / total_tasks, 4) if total_tasks else 0.0
    critic_loop_pass_rate = round(loop_passes / total_tasks, 4) if total_tasks else 0.0
    lift = round(critic_loop_pass_rate - baseline_pass_rate, 4)
    avg_rounds_to_approve = (
        round(sum(approved_rounds) / len(approved_rounds), 2)
        if approved_rounds
        else 0.0
    )
    total_approved_tasks = len(approved_rounds)
    false_approval_rate = (
        round(false_approvals / total_approved_tasks, 4)
        if total_approved_tasks > 0
        else 0.0
    )
    false_rejection_rate = (
        round(false_rejections / total_tasks, 4)
        if total_tasks > 0
        else 0.0
    )
    stall_rate = round(stalls / total_tasks, 4) if total_tasks else 0.0

    # Option A: Critic Catch / Intervention Rate
    critic_intervention_count = sum(1 for t in per_task_results if t["rounds_used"] > 1)
    critic_intervention_rate = round(critic_intervention_count / total_tasks, 4) if total_tasks else 0.0
    revision_success_count = sum(1 for t in per_task_results if t["rounds_used"] > 1 and t["loop_passed"])
    revision_success_rate = round(revision_success_count / critic_intervention_count, 4) if critic_intervention_count > 0 else 1.0

    # Option C: Latency Rollup
    avg_baseline_latency_sec = round(sum(t["baseline_latency_sec"] for t in per_task_results) / total_tasks, 2) if total_tasks else 0.0
    avg_loop_latency_sec = round(sum(t["loop_latency_sec"] for t in per_task_results) / total_tasks, 2) if total_tasks else 0.0

    scorecard: dict[str, Any] = {
        "run_timestamp": timestamp_str,
        "task_count": total_tasks,
        "baseline_pass_rate": baseline_pass_rate,
        "critic_loop_pass_rate": critic_loop_pass_rate,
        "lift": lift,
        "avg_rounds_to_approve": avg_rounds_to_approve,
        "false_approval_rate": false_approval_rate,
        "false_rejection_count": false_rejections,
        "false_rejection_rate": false_rejection_rate,
        "stall_rate": stall_rate,
        "critic_intervention_count": critic_intervention_count,
        "critic_intervention_rate": critic_intervention_rate,
        "revision_success_rate": revision_success_rate,
        "avg_baseline_latency_sec": avg_baseline_latency_sec,
        "avg_loop_latency_sec": avg_loop_latency_sec,
        "per_task_results": per_task_results,
    }

    # Save timestamped JSON scorecard
    report_file = output_dir / f"eval_results_{timestamp_str}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)

    print(f"\n=======================================================")
    print(f"Evaluation Complete! Saved report to: {report_file}")
    print(f"Baseline Pass Rate:       {baseline_pass_rate * 100:.1f}%")
    print(f"Critic Loop Pass Rate:    {critic_loop_pass_rate * 100:.1f}%")
    print(f"Headline Lift:            {lift * 100:+.1f}%")
    print(f"Critic Catch Rate:        {critic_intervention_rate * 100:.1f}% ({critic_intervention_count} tasks caught & revised)")
    print(f"Revision Success Rate:    {revision_success_rate * 100:.1f}%")
    print(f"False Approval Rate:      {false_approval_rate * 100:.1f}% (Rubber-stamping)")
    print(f"False Rejection Rate:     {false_rejection_rate * 100:.1f}% (Hyper-criticism)")
    print(f"Avg Rounds to Approve:    {avg_rounds_to_approve}")
    print(f"Avg Latency (Base vs Loop): {avg_baseline_latency_sec}s vs {avg_loop_latency_sec}s")
    print(f"=======================================================\n")

    return scorecard
