import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

import ast

from tasks.schemas import Task
from tasks.loader import load_task_bank, get_task_by_id
from orchestrator import run_loop
from sandbox.test_runner import run_hidden_tests
from eval.eval_harness import run_evaluation

console = Console()


def execute_task_or_prompt(
    task_id: str | None = None,
    prompt: str | None = None,
    signature: str | None = None,
    max_rounds: int = 3,
):
    """Core execution logic for a task ID or an ad-hoc custom prompt."""
    if not task_id and not prompt:
        console.print(
            "[bold red]Error:[/bold red] Please provide either --task <task_id> or --prompt \"<prompt text>\""
        )
        return

    is_custom = bool(prompt)
    if is_custom:
        sig = (
            signature.strip()
            if signature
            else "Define an idiomatic function signature with type annotations suited to the specification."
        )
        task = Task(
            id="custom_prompt",
            title="Custom Specification",
            spec=prompt.strip(),
            function_signature=sig,
            difficulty="medium",
            hidden_tests="",
        )
    else:
        try:
            task = get_task_by_id(task_id)
        except KeyError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            return

    console.print(
        Panel(
            f"[bold cyan]Task ID:[/bold cyan] {task.id}\n"
            f"[bold cyan]Title:[/bold cyan] {task.title} ({task.difficulty})\n"
            f"[bold cyan]Signature:[/bold cyan] [green]{task.function_signature}[/green]\n\n"
            f"[bold white]{task.spec}[/bold white]",
            title="[bold blue]Task Specification[/bold blue]",
            border_style="blue",
        )
    )

    with console.status(f"[bold yellow]Executing multi-agent loop (up to {max_rounds} rounds)...[/bold yellow]"):
        loop_res = run_loop(task, max_rounds=max_rounds)

    final_code = loop_res["final_code"]
    rounds_used = loop_res["rounds_used"]
    stopped_reason = loop_res["stopped_reason"]
    history = loop_res["verdict_history"]

    console.print(f"\n[bold magenta]=== Round-by-Round Progression ({rounds_used} rounds used) ===[/bold magenta]")
    for item in history:
        rnd = item["round"]
        verdict = item["verdict"]
        summary = item["summary"]
        v_color = "bold green" if verdict == "APPROVE" else "bold red"

        console.print(
            Panel(
                f"[bold]Verdict:[/bold] [{v_color}]{verdict}[/{v_color}]\n"
                f"[bold]Issues Count:[/bold] {item['issues_count']}\n"
                f"[bold]Review Summary:[/bold] {summary}",
                title=f"Round {rnd} Critique",
                border_style="green" if verdict == "APPROVE" else "red",
            )
        )

    console.print("\n[bold cyan]Generated Code:[/bold cyan]")
    syntax = Syntax(final_code, "python", theme="monokai", line_numbers=True)
    console.print(syntax)

    if not is_custom and task.hidden_tests.strip():
        console.print("\n[bold yellow]Running Ground Truth Hidden Tests in Sandbox...[/bold yellow]")
        test_res = run_hidden_tests(final_code, task)

        if test_res["passed"]:
            status_text = "[bold green]ALL TESTS PASSED[/bold green]"
            border = "green"
        else:
            status_text = "[bold red]TESTS FAILED[/bold red]"
            border = "red"

        console.print(
            Panel(
                f"[bold]Result:[/bold] {status_text}\n"
                f"[bold]Pass Count:[/bold] {test_res['pass_count']}\n"
                f"[bold]Fail Count:[/bold] {test_res['fail_count']}\n"
                f"[bold]Stopped Reason:[/bold] {stopped_reason}\n\n"
                f"[bold]Output Trace:[/bold]\n{test_res['output'][:500]}",
                title="Ground Truth Verification",
                border_style=border,
            )
        )
    else:
        # Validate syntax via AST for custom prompts
        try:
            ast.parse(final_code)
            syntax_status = "[bold green]Python AST Parsed Successfully (Valid Syntax)[/bold green]"
            border = "green"
        except SyntaxError as e:
            syntax_status = f"[bold red]Syntax Error:[/bold red] {e}"
            border = "red"

        console.print(
            Panel(
                f"[bold]Syntax Status:[/bold] {syntax_status}\n"
                f"[bold]Stopped Reason:[/bold] {stopped_reason}\n"
                f"[bold]Rounds Used:[/bold] {rounds_used}\n\n"
                f"[dim]Note: Ground-truth unit tests are only bundled for task bank challenges.\n"
                f"For custom prompts, code has been iteratively drafted and critiqued across 5 engineering dimensions.[/dim]",
                title="Custom Prompt Execution Summary",
                border_style=border,
            )
        )


@click.group(invoke_without_command=True)
@click.option("--prompt", "-p", default=None, help="Custom prompt or specification to execute")
@click.option("--signature", "-s", default=None, help="Optional function signature for custom prompt")
@click.option("--task", "--task-id", "-t", "task_id", default=None, help="Task ID or number to execute (e.g., 1, task_001)")
@click.option("--max-rounds", default=3, show_default=True, type=int, help="Maximum critique rounds")
@click.pass_context
def main(
    ctx: click.Context,
    prompt: str | None,
    signature: str | None,
    task_id: str | None,
    max_rounds: int,
):
    """DualCode: Multi-Agent Code Writer & Reviewer CLI."""
    if ctx.invoked_subcommand is None:
        if prompt or task_id:
            execute_task_or_prompt(
                task_id=task_id,
                prompt=prompt,
                signature=signature,
                max_rounds=max_rounds,
            )
        else:
            click.echo(ctx.get_help())


@main.command(name="list")
def list_tasks():
    """List all available tasks in the task bank."""
    tasks = load_task_bank()
    table = Table(title="DualCode - Task Bank", header_style="bold magenta")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold white")
    table.add_column("Difficulty", style="yellow")
    table.add_column("Function Signature", style="green")

    for t in tasks:
        diff_color = {
            "easy": "[green]easy[/green]",
            "medium": "[yellow]medium[/yellow]",
            "hard": "[red]hard[/red]",
        }.get(t.difficulty, t.difficulty)
        table.add_row(t.id, t.title, diff_color, t.function_signature)

    console.print(table)


@main.command(name="run")
@click.option("--task", "--task-id", "-t", "task_id", default=None, help="Task ID or number to execute (e.g., 1, task_001)")
@click.option("--prompt", "-p", default=None, help="Custom prompt or specification to execute")
@click.option("--signature", "-s", default=None, help="Optional function signature for custom prompt")
@click.option("--max-rounds", default=3, show_default=True, type=int, help="Maximum critique rounds")
def run_task(
    task_id: str | None,
    prompt: str | None,
    signature: str | None,
    max_rounds: int,
):
    """Run a task or custom prompt through the full Writer/Critic multi-agent loop with live visualization."""
    execute_task_or_prompt(
        task_id=task_id,
        prompt=prompt,
        signature=signature,
        max_rounds=max_rounds,
    )


@main.command(name="eval")
@click.option("--count", default=None, type=int, help="Number of tasks to evaluate (default: all)")
@click.option("--difficulty", default=None, type=click.Choice(["easy", "medium", "hard"]), help="Filter by difficulty")
@click.option("--max-rounds", default=3, show_default=True, type=int, help="Maximum rounds in DualCode loop")
def evaluate(count: int | None, difficulty: str | None, max_rounds: int):
    """Run the evaluation harness (Baseline vs. DualCode Loop) and render the scorecard."""
    tasks = load_task_bank()
    if difficulty:
        tasks = [t for t in tasks if t.difficulty == difficulty]
    if count:
        tasks = tasks[:count]

    scorecard = run_evaluation(tasks=tasks, max_rounds=max_rounds)

    # Render Scorecard Summary
    console.print("\n")
    summary_table = Table(title="DualCode - Evaluation Scorecard", header_style="bold green")
    summary_table.add_column("Metric", style="bold white")
    summary_table.add_column("Score / Value", style="bold yellow")
    summary_table.add_column("Evaluation Meaning", style="dim")

    summary_table.add_row("Tasks Evaluated", str(scorecard["task_count"]), "Sample size")
    summary_table.add_row(
        "Baseline Pass Rate",
        f"{scorecard['baseline_pass_rate'] * 100:.1f}%",
        "Writer 1-shot without Critic",
    )
    summary_table.add_row(
        "DualCode Pass Rate",
        f"{scorecard['critic_loop_pass_rate'] * 100:.1f}%",
        "Final code after DualCode",
    )
    lift_val = scorecard["lift"]
    lift_str = f"[bold green]+{lift_val*100:.1f}%[/bold green]" if lift_val >= 0 else f"[bold red]{lift_val*100:.1f}%[/bold red]"
    summary_table.add_row("Headline Lift", lift_str, "Improvement from DualCode")
    summary_table.add_row(
        "Critic Catch Rate",
        f"{scorecard.get('critic_intervention_rate', 0.0) * 100:.1f}%",
        f"Critic intervened & rejected round 1 ({scorecard.get('critic_intervention_count', 0)} tasks)",
    )
    summary_table.add_row(
        "Revision Success Rate",
        f"{scorecard.get('revision_success_rate', 1.0) * 100:.1f}%",
        "Intervened tasks that successfully reached passing code",
    )
    summary_table.add_row(
        "False Approval Rate",
        f"{scorecard['false_approval_rate'] * 100:.1f}%",
        "Critic approved but tests failed (Rubber-stamping canary)",
    )
    summary_table.add_row(
        "False Rejection Rate",
        f"{scorecard.get('false_rejection_rate', 0.0) * 100:.1f}%",
        "Tests passed but Critic never approved (Hyper-criticism canary)",
    )
    summary_table.add_row(
        "Stall Rate",
        f"{scorecard['stall_rate'] * 100:.1f}%",
        "Exited due to consecutive code stagnation (>98% similar)",
    )
    summary_table.add_row(
        "Avg Rounds to Approve",
        str(scorecard["avg_rounds_to_approve"]),
        "Average iterations when approved",
    )
    summary_table.add_row(
        "Avg Latency (Base / Loop)",
        f"{scorecard.get('avg_baseline_latency_sec', 0.0)}s / {scorecard.get('avg_loop_latency_sec', 0.0)}s",
        "Wall-clock execution time per task",
    )

    console.print(summary_table)

    # Render Per-Task Breakdown Table
    breakdown_table = Table(title="Per-Task Detailed Breakdown", header_style="bold blue")
    breakdown_table.add_column("Task ID", style="cyan")
    breakdown_table.add_column("Diff", style="dim")
    breakdown_table.add_column("Baseline", justify="center")
    breakdown_table.add_column("Loop", justify="center")
    breakdown_table.add_column("Rounds", justify="center")
    breakdown_table.add_column("Reason")
    breakdown_table.add_column("Anomaly Canary", justify="center")

    for r in scorecard["per_task_results"]:
        base_icon = "[green]PASS[/green]" if r["baseline_passed"] else "[red]FAIL[/red]"
        loop_icon = "[green]PASS[/green]" if r["loop_passed"] else "[red]FAIL[/red]"
        
        if r.get("false_approval"):
            anomaly_icon = "[bold red]FALSE APPROVAL[/bold red]"
        elif r.get("false_rejection"):
            anomaly_icon = "[bold yellow]FALSE REJECTION[/bold yellow]"
        else:
            anomaly_icon = "[green]CLEAN[/green]"

        breakdown_table.add_row(
            r["task_id"],
            r["difficulty"],
            base_icon,
            loop_icon,
            str(r["rounds_used"]),
            r["stopped_reason"],
            anomaly_icon,
        )

    console.print(breakdown_table)


if __name__ == "__main__":
    main()
