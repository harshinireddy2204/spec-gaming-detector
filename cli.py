#!/usr/bin/env python3
"""
Spec Gaming Detector — CLI
Usage:
  python cli.py --task examples/prime_task.py
  python cli.py --task examples/sort_task.py --save
  python cli.py --task examples/fizzbuzz_task.py --save --out reports/fizzbuzz.json
"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()


def load_task_from_file(path: str):
    spec = importlib.util.spec_from_file_location("task_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "task"):
        console.print(f"[red]Error:[/red] {path} must define a top-level variable named `task`")
        sys.exit(1)
    return module.task


def main():
    parser = argparse.ArgumentParser(description="Detect specification gaming in AI-generated solutions")
    parser.add_argument("--task", required=True, help="Path to a task file (e.g. examples/prime_task.py)")
    parser.add_argument("--save", action="store_true", help="Save JSON report to disk")
    parser.add_argument("--out", default=None, help="Output path for JSON report (default: reports/<task_name>.json)")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001", help="Model to use for agent + probes")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    import anthropic
    from detector.runner import AgentRunner
    from detector.probes import ProbeEngine
    from detector.judge import Judge
    from detector.report import Report

    client = anthropic.Anthropic(api_key=api_key)
    task = load_task_from_file(args.task)

    console.print(f"\n[bold cyan]Spec Gaming Detector[/bold cyan]")
    console.print(f"Task: [bold]{task.name}[/bold]")
    console.print(f"Domain: {task.domain}  |  Test cases: {len(task.test_cases)}\n")

    # Step 1: Generate and run the agent solution
    console.print("[dim]Step 1/4  Generating agent solution...[/dim]")
    runner = AgentRunner(client, model=args.model)
    original_run = runner.run(task)
    console.print(f"         Pass rate: {original_run.pass_rate * 100:.0f}% ({original_run.passed}/{original_run.total})")

    if original_run.passed == 0:
        console.print("[yellow]Warning:[/yellow] Agent failed all original tests — solution may be broken. Continuing with probes.")

    # Step 2: Run adversarial probes
    console.print("[dim]Step 2/4  Running adversarial probes (semantic / boundary / transfer)...[/dim]")
    probe_engine = ProbeEngine(client, runner)
    probe_results = probe_engine.run_all(task, original_run.solution_code)
    flagged = sum(1 for p in probe_results if p.flagged)
    console.print(f"         Probes flagged: {flagged}/3")

    # Step 3: Judge
    console.print("[dim]Step 3/4  Running LLM judge...[/dim]")
    judge = Judge(client)
    verdict = judge.judge(task, original_run, probe_results)
    console.print(f"         Gaming score: {verdict.gaming_score}/100  |  Verdict: {verdict.verdict.upper()}")

    # Step 4: Report
    console.print("[dim]Step 4/4  Generating report...[/dim]\n")
    report = Report(task, original_run, probe_results, verdict)
    report.print()

    if args.save:
        out_path = args.out
        if not out_path:
            Path("reports").mkdir(exist_ok=True)
            safe_name = task.name.lower().replace(" ", "_").replace("?", "")
            out_path = f"reports/{safe_name}.json"
        report.save(out_path)


if __name__ == "__main__":
    main()
