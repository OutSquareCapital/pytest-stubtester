"""Tests for the pytest-stubtester plugin."""

from pathlib import Path

import pyochain as pc
import pytest

import pytest_stubtester as pst


def test_plugin_is_registered(pytestconfig: pytest.Config) -> None:
    """Plugin should be registered with pytest."""
    plugin = pytestconfig.pluginmanager.get_plugin("stubtester")
    assert plugin is not None


def test_pyi_enabled_option_exists(pytestconfig: pytest.Config) -> None:
    """--pyi-enabled option should be available."""
    assert hasattr(pytestconfig.option, "stubs")


def test_pyi_module_class_exists() -> None:
    """PyiModule class should exist and inherit from pytest.Module."""
    assert issubclass(pst.PyiModule, pytest.Module)


def test_plugin_disabled_by_default(pytester: pytest.Pytester) -> None:
    """Plugin should not collect .pyi files when disabled."""
    _ = pytester.makefile(
        ".pyi",
        test_sample="""
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.

    >>> 1 + 2
    3
    \"\"\"
""",
    )
    # Should not collect the .pyi file when plugin disabled
    pytester.runpytest("-v").stdout.no_fnmatch_line("*test_sample.pyi*")


def test_plugin_enabled_collects_pyi(pytester: pytest.Pytester) -> None:
    """Plugin should collect .pyi files when enabled."""
    _ = pytester.makefile(
        ".pyi",
        test_sample="""
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.

    >>> 1 + 2
    3
    \"\"\"
""",
    )

    result = pytester.runpytest(pst.COMMAND, "-v")
    # Should collect and pass the doctest
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*test_sample.pyi*PASSED*"])


def test_passing_doctests(pytester: pytest.Pytester) -> None:
    """Valid doctests should pass."""
    _ = pytester.makefile(
        ".pyi",
        passing="""
def multiply(a: int, b: int) -> int:
    \"\"\"Multiply two numbers.

    >>> 3 * 4
    12
    >>> 0 * 100
    0
    \"\"\"
""",
    )

    result = pytester.runpytest(pst.COMMAND, "-v")
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*passing.pyi*PASSED*"])


def test_failing_doctests(pytester: pytest.Pytester) -> None:
    """Invalid doctests should fail."""
    _ = pytester.makefile(
        ".pyi",
        failing="""
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.

    >>> 2 + 2
    5
    \"\"\"
""",
    )

    result = pytester.runpytest(pst.COMMAND, "-v")
    assert result.ret != 0
    result.stdout.fnmatch_lines(["*failing.pyi*FAILED*"])


def test_multiple_doctests_in_file(pytester: pytest.Pytester) -> None:
    """Multiple doctests in one file should all be collected."""
    _ = pytester.makefile(
        ".pyi",
        multi="""
def add(a: int, b: int) -> int:
    \"\"\"Add.

    >>> 1 + 1
    2
    \"\"\"

def sub(a: int, b: int) -> int:
    \"\"\"Subtract.

    >>> 5 - 3
    2
    \"\"\"
""",
    )

    result = pytester.runpytest(pst.COMMAND, "-v")
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*multi.pyi::add*PASSED*"])
    result.stdout.fnmatch_lines(["*multi.pyi::sub*PASSED*"])


def test_non_pyi_files_ignored(pytester: pytest.Pytester) -> None:
    """Non-.pyi files should be ignored even with plugin enabled."""
    _ = pytester.makefile(
        ".txt",
        readme="""
>>> 1 + 1
2
""",
    )

    result = pytester.runpytest(pst.COMMAND, "-v")
    # Should not collect .txt file
    result.stdout.no_fnmatch_line("*readme.txt*")


def test_empty_pyi_file(pytester: pytest.Pytester) -> None:
    """Empty .pyi file should not cause errors."""
    _ = pytester.makefile(".pyi", empty="")

    result = pytester.runpytest(pst.COMMAND, "-v")
    # Should complete without errors, just no tests collected from this file
    assert "error" not in result.stdout.str().lower()


def test_pyi_file_without_doctests(pytester: pytest.Pytester) -> None:
    """.pyi file without doctests should not collect any tests."""
    _ = pytester.makefile(
        ".pyi",
        no_doctests="""
def function_without_docstring(x: int) -> int: ...

def function_with_docstring_no_tests(x: int) -> int:
    \"\"\"This function has no doctests.\"\"\"
""",
    )

    result = pytester.runpytest(pst.COMMAND, "-v", "--collect-only")
    # File with no doctests returns exit code 5 (NO_TESTS_COLLECTED)
    no_tests_collected = 5
    assert result.ret == no_tests_collected


def test_real_success_examples() -> None:
    """Real example files in tests/examples/success should exist."""
    success_dir = Path("tests", "examples", "success")
    assert success_dir.exists()

    assert pc.Iter(success_dir.glob("*.pyi")).length() > 0, (
        "Should have .pyi test files in success/"
    )


def test_real_failure_examples() -> None:
    """Real example files in tests/examples/failures should exist."""
    failures_dir = Path("tests", "examples", "failures")
    assert failures_dir.exists()

    assert pc.Iter(failures_dir.glob("*.pyi")).length() > 0, (
        "Should have .pyi test files in failures/"
    )
