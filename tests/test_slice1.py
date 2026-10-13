import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collections import Counter
from tasks.loader import load_task_bank
from tasks.schemas import Task


def test_slice1_task_bank_validation():
    tasks = load_task_bank()
    assert len(tasks) >= 12, f"Expected at least 12 tasks, found {len(tasks)}"

    counts = Counter(t.difficulty for t in tasks)
    print("\n--- Slice 1 Acceptance Test Summary ---")
    print(f"Total tasks loaded: {len(tasks)}")
    for difficulty in ["easy", "medium", "hard"]:
        count = counts.get(difficulty, 0)
        print(f"  • {difficulty.capitalize()}: {count}")
        assert count > 0, f"Expected at least one {difficulty} task"

    # Validate each task has non-empty fields
    for t in tasks:
        assert isinstance(t, Task)
        assert t.id.strip()
        assert t.title.strip()
        assert t.spec.strip()
        assert t.function_signature.startswith("def ")
        assert "def test_" in t.hidden_tests


if __name__ == "__main__":
    test_slice1_task_bank_validation()
