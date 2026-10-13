import ast
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tasks.loader import get_task_by_id
from tasks.schemas import Issue, CritiqueResult
from agents.writer import write_code


def test_slice2_writer_agent():
    test_task_ids = ["task_001", "task_002"]

    print("\n--- Slice 2 Acceptance Test: Initial Code Generation ---")
    for task_id in test_task_ids:
        task = get_task_by_id(task_id)
        print(f"\n[Task {task.id}: {task.title}]")
        output = write_code(task)

        assert output.round_number == 1
        assert len(output.code.strip()) > 0

        # Syntax check via AST parse
        parsed_ast = ast.parse(output.code)
        func_names = [n.name for n in ast.walk(parsed_ast) if isinstance(n, ast.FunctionDef)]
        print(f"Functions defined in generated code: {func_names}")
        print("Generated Code snippet:")
        print("----------------------------------------")
        print(output.code)
        print("----------------------------------------")
        assert len(func_names) > 0, "Expected at least one function definition in generated code"

    # Test Round 2 Revision flow
    print("\n--- Slice 2 Acceptance Test: Round 2 Revision Flow ---")
    task = get_task_by_id("task_001")
    flawed_code = "def reverse_words(sentence: str) -> str:\n    return ' '.join(sentence.split(' '))"
    mock_critique = CritiqueResult(
        verdict="REVISE",
        summary="Code fails to handle multiple consecutive whitespaces and leading/trailing spaces correctly.",
        issues=[
            Issue(
                category="edge_case",
                severity="critical",
                explanation="sentence.split(' ') preserves empty strings when multiple spaces are present.",
                suggestion="Use sentence.split() without arguments to split on any whitespace sequence."
            )
        ]
    )

    revised_output = write_code(task, previous_code=flawed_code, critique=mock_critique, round_number=2)
    assert revised_output.round_number == 2
    ast.parse(revised_output.code)
    print("Revised Code from Round 2:")
    print("----------------------------------------")
    print(revised_output.code)
    print("----------------------------------------")


if __name__ == "__main__":
    test_slice2_writer_agent()
