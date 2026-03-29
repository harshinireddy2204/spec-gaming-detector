import json
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .task import TaskSpec
from .runner import RunResult
from .probes import ProbeResult
from .judge import Verdict

console = Console()


def _verdict_color(verdict: str) -> str:
    return {"clean": "green", "suspicious": "yellow", "gaming": "red"}.get(verdict, "white")


def _score_bar(score: int, width: int = 20) -> str:
    filled = round(score / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    return bar


class Report:
    def __init__(
        self,
        task: TaskSpec,
        original_run: RunResult,
        probe_results: list[ProbeResult],
        verdict: Verdict,
    ):
        self.task = task
        self.original_run = original_run
        self.probe_results = probe_results
        self.verdict = verdict

    def print(self) -> None:
        v = self.verdict
        color = _verdict_color(v.verdict)

        console.print()
        console.rule(f"[bold]Spec Gaming Detector — {self.task.name}[/bold]")
        console.print()

        # --- Verdict banner ---
        bar = _score_bar(v.gaming_score)
        verdict_text = Text()
        verdict_text.append(f"  {v.verdict.upper()}  ", style=f"bold white on {color}")
        verdict_text.append(f"  Gaming score: {v.gaming_score}/100  ", style=f"bold {color}")
        verdict_text.append(f"[{bar}]  ", style=color)
        verdict_text.append(f"Type: {v.gaming_type}  ", style="dim")
        verdict_text.append(f"Confidence: {v.confidence}", style="dim")
        console.print(Panel(verdict_text, border_style=color))

        # --- Original run ---
        console.print(f"\n[bold]Original solution[/bold] — pass rate: [cyan]{self.original_run.pass_rate * 100:.0f}%[/cyan] ({self.original_run.passed}/{self.original_run.total})\n")
        console.print(
            Panel(
                self.original_run.solution_code,
                title="solution code",
                border_style="dim",
                padding=(0, 1),
            )
        )

        # --- Probe results ---
        console.print("\n[bold]Adversarial probe results[/bold]\n")
        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
        table.add_column("Probe", style="dim", width=22)
        table.add_column("Variant task (truncated)", width=36)
        table.add_column("Pass rate", justify="center", width=10)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Note", width=34)

        for p in self.probe_results:
            status = "[red]FLAGGED[/red]" if p.flagged else "[green]OK[/green]"
            rate_color = "red" if p.pass_rate < 0.5 else ("yellow" if p.pass_rate < 0.8 else "green")
            desc = p.variant_task.description[:60] + "…" if len(p.variant_task.description) > 60 else p.variant_task.description
            table.add_row(
                p.probe_type,
                desc,
                f"[{rate_color}]{p.pass_rate * 100:.0f}%[/{rate_color}]",
                status,
                p.note[:60] + "…" if len(p.note) > 60 else p.note,
            )
        console.print(table)

        # --- Evidence ---
        console.print("[bold]Evidence[/bold]\n")
        for i, ev in enumerate(v.evidence, 1):
            console.print(f"  {i}. {ev}")

        # --- Fix hint ---
        console.print(f"\n[bold]Fix hint:[/bold] [italic]{v.fix_hint}[/italic]\n")
        console.rule()
        console.print()

    def to_dict(self) -> dict:
        return {
            "task": self.task.name,
            "timestamp": datetime.utcnow().isoformat(),
            "original_pass_rate": self.original_run.pass_rate,
            "solution_code": self.original_run.solution_code,
            "probes": [
                {
                    "type": p.probe_type,
                    "pass_rate": p.pass_rate,
                    "flagged": p.flagged,
                    "note": p.note,
                }
                for p in self.probe_results
            ],
            "verdict": {
                "gaming_score": self.verdict.gaming_score,
                "verdict": self.verdict.verdict,
                "gaming_type": self.verdict.gaming_type,
                "evidence": self.verdict.evidence,
                "confidence": self.verdict.confidence,
                "fix_hint": self.verdict.fix_hint,
            },
        }

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        console.print(f"[dim]Report saved to {path}[/dim]")
