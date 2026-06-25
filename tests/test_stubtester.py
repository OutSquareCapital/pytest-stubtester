"""Tests for the pytest-stubtester plugin."""

from __future__ import annotations

from pathlib import Path

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


def test_success_examples_all_pass(pytester: pytest.Pytester) -> None:
    """All .pyi files in tests/examples/success should pass."""
    result = pytester.runpytest(
        pst.COMMAND,
        "-v",
        str(Path(__file__).parent / "examples" / "success"),
    )
    assert result.ret == 0


def test_failure_examples_have_failures(pytester: pytest.Pytester) -> None:
    """tests/examples/failures should contain failing doctests."""
    result = pytester.runpytest(
        pst.COMMAND,
        "-v",
        str(Path(__file__).parent / "examples" / "failures"),
    )
    assert result.ret != 0


def test_class_doctest(pytester: pytest.Pytester) -> None:
    """Class-level docstring with doctests should be collected and run."""
    _ = pytester.makefile(
        ".pyi",
        cls_test="""
class MyClass:
    \"\"\"My class.

    >>> 1 + 1
    2
    \"\"\"
""",
    )
    result = pytester.runpytest(pst.COMMAND, "-v")
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*cls_test.pyi::MyClass*PASSED*"])


def test_class_method_doctest(pytester: pytest.Pytester) -> None:
    """Method inside a class should be collected as ClassName.method_name."""
    _ = pytester.makefile(
        ".pyi",
        cls_method="""
class MyClass:
    def my_method(self) -> int:
        \"\"\"Method.

        >>> 3 + 3
        6
        \"\"\"
""",
    )
    result = pytester.runpytest(pst.COMMAND, "-v")
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*cls_method.pyi::MyClass.my_method*PASSED*"])


def test_markdown_fence_doctest(pytester: pytest.Pytester) -> None:
    """Doctests inside markdown code fences should be extracted and run."""
    _ = pytester.makefile(
        ".pyi",
        markdown="""
def foo() -> int:
    \"\"\"Function with markdown fence.

    ```python
    >>> 1 + 1
    2
    >>> 2 + 2
    4
    ```
    \"\"\"
""",
    )
    result = pytester.runpytest(pst.COMMAND, "-v")
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*markdown.pyi::foo*PASSED*"])
