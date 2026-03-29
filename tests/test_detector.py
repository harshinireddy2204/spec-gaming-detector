"""
Unit tests for Spec Gaming Detector components.
Run with: pytest tests/ -v
"""
import pytest
from detector.task import TaskSpec, TestCase
from detector.runner import AgentRunner
from detector.ast_analysis import detect_hardcoding


# ------------------------------------------------------------------ #
#  Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def simple_task():
    return TaskSpec(
        name="Add two numbers",
        description="Write a function that adds two integers.",
        domain="coding",
        test_cases=[
            TestCase(input=[1, 2], expected=3),
            TestCase(input=[0, 0], expected=0),
            TestCase(input=[-1, 1], expected=0),
        ],
    )


# ------------------------------------------------------------------ #
#  AST analysis tests                                                   #
# ------------------------------------------------------------------ #

def test_detect_hardcoded_values():
    code = """
def is_prime(n):
    known = {2, 3, 5, 7, 11}
    return n in known
"""
    cases = [
        TestCase(input=2, expected=True),
        TestCase(input=3, expected=True),
        TestCase(input=4, expected=False),
    ]
    result = detect_hardcoding(code, cases)
    assert result["suspicion_level"] in ("medium", "high")


def test_clean_solution_not_flagged():
    code = """
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
"""
    cases = [
        TestCase(input=2, expected=True),
        TestCase(input=4, expected=False),
    ]
    result = detect_hardcoding(code, cases)
    assert result["suspicion_level"] == "low"
    assert result["has_loop"] is True


def test_syntax_error_handled():
    result = detect_hardcoding("def broken(", [])
    assert result["suspicion_level"] == "unknown"


# ------------------------------------------------------------------ #
#  Runner tests (no API calls)                                          #
# ------------------------------------------------------------------ #

def test_runner_executes_correct_solution(simple_task):
    class MockClient:
        pass

    runner = AgentRunner(MockClient())
    code = """
def add(a, b):
    return a + b
"""
    results = runner.execute_solution(code, simple_task.test_cases)
    assert all(r["passed"] for r in results)


def test_runner_catches_wrong_output(simple_task):
    class MockClient:
        pass

    runner = AgentRunner(MockClient())
    code = """
def add(a, b):
    return 999
"""
    results = runner.execute_solution(code, simple_task.test_cases)
    assert not any(r["passed"] for r in results)


def test_runner_handles_syntax_error(simple_task):
    class MockClient:
        pass

    runner = AgentRunner(MockClient())
    results = runner.execute_solution("def broken(", simple_task.test_cases)
    assert all(not r["passed"] for r in results)
    assert "SyntaxError" in results[0]["error"]


# ------------------------------------------------------------------ #
#  Task spec tests                                                       #
# ------------------------------------------------------------------ #

def test_task_builds_prompt(simple_task):
    prompt = simple_task.build_prompt()
    assert "Write a function that adds two integers" in prompt
    assert "Test cases" in prompt


def test_task_with_custom_prompt():
    task = TaskSpec(
        name="Custom",
        description="Do something",
        test_cases=[TestCase(input=1, expected=2)],
        agent_prompt_template="Custom prompt here",
    )
    assert task.build_prompt() == "Custom prompt here"
