import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tasks.loader import get_task_by_id
from tasks.schemas import CritiqueResult
from agents.critic import review_code


def test_slice3_critic_broken_code():
    print("\n--- Slice 3 Acceptance Test: Broken Code Review ---")
    task = get_task_by_id("task_001")  # Reverse words

    # Deliberately broken: splits words and joins them, but completely forgets to reverse!
    broken_code = """def reverse_words(sentence: str) -> str:
    words = sentence.split()
    return " ".join(words)
"""
    result = review_code(task, broken_code)
    print(f"Broken Code Verdict: {result.verdict}")
    print(f"Summary: {result.summary}")
    for idx, issue in enumerate(result.issues, 1):
        print(f"  Issue {idx}: [{issue.category}] {issue.explanation}")

    assert isinstance(result, CritiqueResult)
    assert result.verdict == "REVISE", f"Expected REVISE for broken code, got {result.verdict}"
    assert len(result.issues) > 0, "Expected at least one itemized issue for broken code"
    categories = [i.category for i in result.issues]
    assert "correctness" in categories or "edge_case" in categories, (
        f"Expected correctness/edge_case category, got {categories}"
    )


def test_slice3_critic_correct_code():
    print("\n--- Slice 3 Acceptance Test: Correct Code Review ---")
    task = get_task_by_id("task_001")

    # Correct, clean implementation
    correct_code = """def reverse_words(sentence: str) -> str:
    return " ".join(sentence.split()[::-1])
"""
    result = review_code(task, correct_code)
    print(f"Correct Code Verdict: {result.verdict}")
    print(f"Summary: {result.summary}")
    print(f"Issues count: {len(result.issues)}")

    assert isinstance(result, CritiqueResult)
    assert result.verdict == "APPROVE", f"Expected APPROVE for correct code, got {result.verdict}"


if __name__ == "__main__":
    test_slice3_critic_broken_code()
    test_slice3_critic_correct_code()
