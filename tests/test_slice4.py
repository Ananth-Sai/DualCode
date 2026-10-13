import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tasks.schemas import Task, WriterOutput, CritiqueResult, Issue
from orchestrator import run_loop, calculate_similarity

# Dummy task for mocked orchestrator tests
DUMMY_TASK = Task(
    id="test_mock_task",
    title="Mock Task",
    spec="Do something",
    function_signature="def mock_func():",
    difficulty="easy",
    hidden_tests="def test_dummy(): pass",
)


def test_slice4_stop_condition_approved():
    print("\n--- Slice 4 Test: Stop Condition 'approved' ---")

    def mock_writer(task, previous_code=None, critique=None, round_number=1):
        if round_number == 1:
            return WriterOutput(code="def mock_func(): return False", round_number=1)
        return WriterOutput(code="def mock_func(): return True", round_number=2)

    def mock_critic(task, code):
        if "return True" in code:
            return CritiqueResult(verdict="APPROVE", issues=[], summary="Approved on round 2")
        return CritiqueResult(
            verdict="REVISE",
            issues=[
                Issue(
                    category="correctness",
                    severity="critical",
                    explanation="Should return True",
                    suggestion="Return True",
                )
            ],
            summary="Needs revision",
        )

    res = run_loop(DUMMY_TASK, max_rounds=3, writer_fn=mock_writer, critic_fn=mock_critic)
    print("Result:", res)
    assert res["stopped_reason"] == "approved"
    assert res["rounds_used"] == 2
    assert len(res["verdict_history"]) == 2
    assert res["verdict_history"][0]["verdict"] == "REVISE"
    assert res["verdict_history"][1]["verdict"] == "APPROVE"
    assert res["final_code"] == "def mock_func(): return True"


def test_slice4_stop_condition_max_rounds():
    print("\n--- Slice 4 Test: Stop Condition 'max_rounds' ---")

    # Writer produces slightly different code each round to avoid triggering stall
    def mock_writer(task, previous_code=None, critique=None, round_number=1):
        return WriterOutput(code=f"def mock_func(): # attempt {round_number}\n    return {round_number}", round_number=round_number)

    # Critic rejects every attempt
    def mock_critic(task, code):
        return CritiqueResult(
            verdict="REVISE",
            issues=[
                Issue(
                    category="correctness",
                    severity="critical",
                    explanation="Never correct",
                    suggestion="Try again",
                )
            ],
            summary="Still incorrect",
        )

    res = run_loop(DUMMY_TASK, max_rounds=3, writer_fn=mock_writer, critic_fn=mock_critic)
    print("Result:", res)
    assert res["stopped_reason"] == "max_rounds"
    assert res["rounds_used"] == 3
    assert len(res["verdict_history"]) == 3
    for v in res["verdict_history"]:
        assert v["verdict"] == "REVISE"


def test_slice4_stop_condition_stalled():
    print("\n--- Slice 4 Test: Stop Condition 'stalled' ---")

    # Writer returns identical code on round 2 (stuck)
    def mock_writer(task, previous_code=None, critique=None, round_number=1):
        return WriterOutput(code="def mock_func(): return 'stuck'", round_number=round_number)

    def mock_critic(task, code):
        return CritiqueResult(
            verdict="REVISE",
            issues=[
                Issue(
                    category="correctness",
                    severity="critical",
                    explanation="Fix this",
                    suggestion="Do something else",
                )
            ],
            summary="Revision needed",
        )

    res = run_loop(DUMMY_TASK, max_rounds=3, stall_threshold=0.98, writer_fn=mock_writer, critic_fn=mock_critic)
    print("Result:", res)
    assert res["stopped_reason"] == "stalled"
    assert res["rounds_used"] == 2
    # Only round 1 verdict is recorded because round 2 stalled before calling critic
    assert len(res["verdict_history"]) == 1


def test_calculate_similarity():
    # Exactly identical
    assert calculate_similarity("abc", "abc") == 1.0
    # Completely different
    assert calculate_similarity("aaaa", "bbbb") == 0.0


if __name__ == "__main__":
    test_calculate_similarity()
    test_slice4_stop_condition_approved()
    test_slice4_stop_condition_max_rounds()
    test_slice4_stop_condition_stalled()
    print("\nAll Slice 4 unit tests passed successfully!")
