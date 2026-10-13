import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tasks.loader import get_task_by_id
from sandbox.test_runner import run_hidden_tests


def test_slice5_known_correct():
    print("\n--- Slice 5 Test: Known-Correct Implementation ---")
    task = get_task_by_id("task_001")
    correct_code = """def reverse_words(sentence: str) -> str:
    return " ".join(sentence.split()[::-1])
"""
    result = run_hidden_tests(correct_code, task)
    print("Correct implementation result:", result)
    assert result["passed"] is True
    assert result["pass_count"] > 0
    assert result["fail_count"] == 0


def test_slice5_known_broken():
    print("\n--- Slice 5 Test: Known-Broken Implementation ---")
    task = get_task_by_id("task_001")
    broken_code = """def reverse_words(sentence: str) -> str:
    return sentence  # Does not reverse!
"""
    result = run_hidden_tests(broken_code, task)
    print("Broken implementation result:", result)
    assert result["passed"] is False
    assert result["fail_count"] > 0


def test_slice5_timeout_handling():
    print("\n--- Slice 5 Test: Infinite Loop / Timeout Handling ---")
    task = get_task_by_id("task_001")
    infinite_loop_code = """def reverse_words(sentence: str) -> str:
    while True:
        pass
"""
    result = run_hidden_tests(infinite_loop_code, task, timeout_seconds=1)
    print("Timeout result:", result)
    assert result["passed"] is False
    assert "timed out" in result["output"].lower()


if __name__ == "__main__":
    test_slice5_known_correct()
    test_slice5_known_broken()
    test_slice5_timeout_handling()
    print("\nAll Slice 5 tests passed successfully!")
