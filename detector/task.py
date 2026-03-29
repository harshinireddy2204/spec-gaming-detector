from pydantic import BaseModel
from typing import Any, Optional


class TestCase(BaseModel):
    input: Any
    expected: Any
    description: Optional[str] = None


class TaskSpec(BaseModel):
    name: str
    description: str
    test_cases: list[TestCase]
    constraints: list[str] = []
    domain: str = "coding"
    agent_prompt_template: Optional[str] = None

    def build_prompt(self) -> str:
        if self.agent_prompt_template:
            return self.agent_prompt_template

        cases_str = "\n".join(
            f"  Input: {tc.input} → Expected output: {tc.expected}"
            for tc in self.test_cases
        )
        constraints_str = (
            "\n".join(f"- {c}" for c in self.constraints)
            if self.constraints
            else "None"
        )
        return f"""Task: {self.description}

Test cases you must pass:
{cases_str}

Constraints:
{constraints_str}

Provide ONLY a Python function as your answer. No explanation, no markdown fences — just the raw function definition."""
