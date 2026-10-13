import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tasks.loader import get_task_by_id
from eval.eval_harness import run_evaluation


def test_slice6_eval_harness_integration(tmp_path):
    print("\n--- Slice 6 & 7 Test: Eval Harness Execution ---")
    test_tasks = [get_task_by_id("task_001")]

    scorecard = run_evaluation(tasks=test_tasks, max_rounds=2, output_dir=tmp_path)

    # Validate Scorecard schema
    assert scorecard["task_count"] == 1
    assert "baseline_pass_rate" in scorecard
    assert "critic_loop_pass_rate" in scorecard
    assert "lift" in scorecard
    assert "false_approval_rate" in scorecard
    assert "stall_rate" in scorecard
    assert len(scorecard["per_task_results"]) == 1

    task_entry = scorecard["per_task_results"][0]
    assert task_entry["task_id"] == "task_001"
    assert "baseline_passed" in task_entry
    assert "loop_passed" in task_entry
    assert "rounds_used" in task_entry
    assert "stopped_reason" in task_entry

    # Check that output JSON was persisted to disk
    json_files = list(tmp_path.glob("eval_results_*.json"))
    assert len(json_files) == 1
    with open(json_files[0], "r", encoding="utf-8") as f:
        loaded_json = json.load(f)
    assert loaded_json["task_count"] == 1
    print("Successfully generated and validated scorecard JSON!")


if __name__ == "__main__":
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as td:
        test_slice6_eval_harness_integration(Path(td))
