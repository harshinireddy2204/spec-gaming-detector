import ast
import traceback
from typing import Any

import anthropic
from pydantic import BaseModel

from .task import TaskSpec


class RunResult(BaseModel):
    solution_code: str
    test_results: list[dict]
    passed: int
    total: int
    pass_rate: float
    error: str = ""


class AgentRunner:
    def __init__(self, client: anthropic.Anthropic, model: str = "claude-haiku-4-5-20251001"):
        self.client = client
        self.model = model

    def generate_solution(self, task: TaskSpec) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": task.build_prompt(),
                }
            ],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if the model added them anyway
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return raw.strip()

    def execute_solution(self, code: str, test_cases: list) -> list[dict]:
        results = []
        namespace: dict[str, Any] = {}

        try:
            exec(compile(ast.parse(code), "<solution>", "exec"), namespace)
        except SyntaxError as e:
            return [
                {
                    "input": tc.input,
                    "expected": tc.expected,
                    "actual": None,
                    "passed": False,
                    "error": f"SyntaxError: {e}",
                }
                for tc in test_cases
            ]

        # Find the first callable in the namespace (the submitted function)
        fn = next(
            (v for v in namespace.values() if callable(v) and not isinstance(v, type)),
            None,
        )
        if fn is None:
            return [
                {
                    "input": tc.input,
                    "expected": tc.expected,
                    "actual": None,
                    "passed": False,
                    "error": "No callable function found in solution",
                }
                for tc in test_cases
            ]

        for tc in test_cases:
            try:
                inp = tc.input
                # If input is a plain list and the function takes multiple args, unpack it
                if isinstance(inp, list):
                    try:
                        actual = fn(*inp)
                    except TypeError:
                        actual = fn(inp)
                else:
                    actual = fn(inp)
                passed = actual == tc.expected
                results.append(
                    {
                        "input": inp,
                        "expected": tc.expected,
                        "actual": actual,
                        "passed": passed,
                        "error": "",
                    }
                )
            except Exception:
                results.append(
                    {
                        "input": tc.input,
                        "expected": tc.expected,
                        "actual": None,
                        "passed": False,
                        "error": traceback.format_exc(limit=2),
                    }
                )
        return results

    def run(self, task: TaskSpec) -> RunResult:
        code = self.generate_solution(task)
        results = self.execute_solution(code, task.test_cases)
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        return RunResult(
            solution_code=code,
            test_results=results,
            passed=passed,
            total=total,
            pass_rate=round(passed / total, 2) if total else 0.0,
        )
