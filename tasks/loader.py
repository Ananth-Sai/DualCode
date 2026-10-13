import json
from pathlib import Path
from tasks.schemas import Task

TASK_BANK_PATH = Path(__file__).parent / "task_bank.json"


def load_task_bank(path: Path | str = TASK_BANK_PATH) -> list[Task]:
    """Load and validate all tasks from the task bank JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        raw_tasks = json.load(f)
    return [Task.model_validate(item) for item in raw_tasks]


def normalize_task_id(task_id: str) -> str:
    """Normalize task IDs such that '1', 'task1', 'task_1', and 'task_001' all resolve to 'task_001'."""
    tid = task_id.strip().lower()
    if tid.isdigit():
        return f"task_{int(tid):03d}"
    if tid.startswith("task"):
        suffix = tid[4:].lstrip("_")
        if suffix.isdigit():
            return f"task_{int(suffix):03d}"
    return tid


def get_task_by_id(task_id: str, path: Path | str = TASK_BANK_PATH) -> Task:
    """Retrieve a single validated task by its ID, supporting flexible numeric shortcuts."""
    tasks = load_task_bank(path)
    normalized = normalize_task_id(task_id)
    for task in tasks:
        if task.id == task_id or task.id == normalized:
            return task
    raise KeyError(f"Task with id '{task_id}' not found in task bank.")
