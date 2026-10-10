"""The gate, tested on its own terms.

What matters is not that the stages pass today, but that each one can fail the
gate, that the exit code says which, and that no skip is silent.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tools.verify import STAGES, Stage, Step, main, step_env


def _always_ok(_step: Step) -> int:
    return 0


def test_twelve_stages_in_order() -> None:
    """TESTING.md declares twelve. A thirteenth is a specification change."""
    assert len(STAGES) == 12
    assert [s.name for s in STAGES] == [
        "format",
        "lint",
        "types",
        "structure",
        "unit",
        "contract",
        "golden",
        "e2e_fake",
        "ui",
        "coverage",
        "openapi",
        "publication",
    ]


def test_stage_names_are_unique() -> None:
    names = [s.name for s in STAGES]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("number", range(1, len(STAGES) + 1))
def test_each_stage_can_fail(number: int, capsys: pytest.CaptureFixture[str]) -> None:
    """A forced failure in each stage exits with that stage's number."""
    stages = _stages_with_no_missing_inputs()
    target = stages[number - 1]

    def runner(step: Step) -> int:
        return 1 if step in target.steps else 0

    assert main([], runner=runner, stages=stages) == number
    assert target.name in capsys.readouterr().err


def test_a_green_run_exits_zero() -> None:
    assert main([], runner=_always_ok, stages=_stages_with_no_missing_inputs()) == 0


def test_stops_at_the_first_failure(capsys: pytest.CaptureFixture[str]) -> None:
    stages = _stages_with_no_missing_inputs()
    ran: list[str] = []

    def runner(step: Step) -> int:
        ran.append(step.argv[-1])
        return 1 if step in stages[1].steps else 0

    assert main([], runner=runner, stages=stages) == 2
    expected = len(stages[0].steps) + 1  # stage one in full, then one step of stage two
    assert len(ran) == expected, "the gate ran past the step that failed"


def test_list_reports_every_stage(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--list"], runner=_always_ok) == 0
    printed = capsys.readouterr().out
    for stage in STAGES:
        assert stage.name in printed


def test_an_unknown_stage_is_refused() -> None:
    assert main(["--stage", "nope"], runner=_always_ok) == 64


def test_one_stage_can_be_run_alone() -> None:
    stages = _stages_with_no_missing_inputs()
    assert main(["--stage", "lint"], runner=_always_ok, stages=stages) == 0


def test_regenerating_goldens_runs_no_stage(capsys: pytest.CaptureFixture[str]) -> None:
    """Regenerating is never the gate: it writes the goldens and stops."""
    from tools.verify import ROOT

    ran: list[Step] = []
    written = [ROOT / "tests" / "golden" / "data" / "plan.py"]

    def runner(step: Step) -> int:
        ran.append(step)
        return 0

    assert main(["--regenerate-goldens"], runner=runner, regenerate=lambda: written) == 0
    assert ran == []
    assert "plan.py" in capsys.readouterr().out


def test_there_is_no_flag_that_relaxes_a_stage() -> None:
    """The gate's own promise: no --skip, no --fast, no --no-verify."""
    import inspect

    import tools.verify as module

    source = inspect.getsource(module)
    for forbidden in ('"--skip"', '"--fast"', '"--no-verify"', '"--ignore"'):
        assert forbidden not in source, f"the gate grew {forbidden}"


def test_every_skippable_step_names_what_is_missing() -> None:
    """A skip is computed from the tree and always states its reason."""
    skippable = [(stage.name, step) for stage in STAGES for step in stage.steps if step.needs]
    assert skippable, "no step declares its inputs, so no skip could be explained"
    for name, step in skippable:
        assert all(path for path in step.needs), f"{name} declares an empty need"


def test_a_step_unskips_once_its_input_exists() -> None:
    """The skip is not a permanent hole: it closes when the input appears."""
    step = Step(("true",), needs=("definitely/absent/path",))
    assert step.missing_input() == "definitely/absent/path"
    live = Step(("true",), needs=("pyproject.toml",))
    assert live.missing_input() is None


def test_a_missing_tool_fails_rather_than_skips(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An absent toolchain is a failure, not a quiet pass."""
    stage = Stage(
        "format",
        "x",
        (Step(("nope",), needs=("pyproject.toml",), tool="definitely-not-a-tool"),),
    )
    assert main([], runner=_always_ok, stages=(stage,)) == 1
    assert "not on the path" in capsys.readouterr().out


def test_interface_steps_run_inside_ui() -> None:
    """The interface toolchain finds its configuration from ui/, so it runs there."""
    for stage in STAGES:
        for step in stage.steps:
            if step.tool == "npx":
                assert step.cwd == "ui", f"{stage.name}: {step.argv} runs outside ui/"


def test_ui_stage_runs_the_three_layers_in_order() -> None:
    """REBUILD-UI.md section 14.4: unit, then component, then end to end."""
    ui = next(s for s in STAGES if s.name == "ui")
    assert [step.argv[2:] for step in ui.steps] == [
        ("vitest", "run", "--project=unit"),
        ("vitest", "run", "--project=storybook"),
        ("playwright", "test"),
    ]


def test_steps_name_the_gates_python() -> None:
    """The contrast oracle runs under the same interpreter as the gate."""
    import sys

    assert step_env()["ROMSYNC_PYTHON"] == sys.executable


def _stages_with_no_missing_inputs() -> Sequence[Stage]:
    """The real stage list with the `needs` stripped.

    The gate's behaviour under failure is what is under test here, not which
    inputs happen to exist in this tree.
    """
    return tuple(
        Stage(
            s.name,
            s.description,
            tuple(Step(step.argv) for step in s.steps),
        )
        for s in STAGES
    )
