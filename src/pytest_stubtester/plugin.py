"""Pytest plugin for discovering and running doctests from .pyi stub files."""

import ast
import doctest
import re
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from typing import NamedTuple, TypeIs, override

import pyochain as pc
import pytest

type IsDef = ast.FunctionDef | ast.ClassDef
COMMAND = "--stubs"
MARKDOWN_BLOCK = re.compile(r"```python\n(.*?)\n```")


class Parsed(NamedTuple):
    """Parsed doctest information."""

    name: str
    """Module or object name."""
    docstring: str
    """Docstring containing the doctest."""
    lineno: int
    """Line number in the source file."""

    def to_doctest(self, path: Path) -> tuple[str, doctest.DocTest]:
        """Convert the parsed information to a doctest.

        Args:
            path (Path): Path to the source file for error reporting.

        Returns:
            tuple[str, doctest.DocTest]: A tuple of the test name and the corresponding doctest object.

        """

        def _extract_markdown_code_blocks() -> str:
            return (
                pc
                .Iter(MARKDOWN_BLOCK.findall(self.docstring))
                .then(lambda m: m.join("\n"))
                .unwrap_or(self.docstring)
            )

        return (
            self.name,
            doctest.DocTestParser().get_doctest(
                _extract_markdown_code_blocks(),
                globs={},
                name=self.name,
                filename=str(path),
                lineno=self.lineno,
            ),
        )


class PyiModule(pytest.Module):
    """Custom pytest Module for collecting doctests from .pyi files."""

    @override
    def collect(self) -> Iterator[pytest.Item]:
        """Collect all doctests from the .pyi file.

        Returns:
            Iterator[pytest.Item]: An iterator of pytest items to be executed.

        """

        def _extract_doctests_from_ast() -> pc.Iter[Parsed]:
            try:
                tree_res = pc.Ok(
                    ast.parse(
                        self.path.read_text(encoding="utf-8"),
                        filename=str(self.path),
                    )
                )
            except SyntaxError:
                tree_res = pc.Err(None)

            match tree_res:
                case pc.Ok(tree):
                    module_doc = _get_doc(tree)
                    module_tests = (
                        pc.Iter.once(Parsed(self.path.stem, module_doc.unwrap(), 1))
                        if module_doc.is_some()
                        else pc.Iter[Parsed].new()
                    )

                    return module_tests.chain(
                        pc
                        .Iter(tree.body)
                        .filter(_is_def)
                        .flat_map(_recurse_extract)
                        .map_star(Parsed)
                    )
                case _:
                    return pc.Iter[Parsed].new()

        return (
            _extract_doctests_from_ast()
            .map(lambda parsed: parsed.to_doctest(self.path))
            .filter_star(lambda _, test: bool(test.examples))
            .map_star(
                lambda name, test: pytest.Function.from_parent(  # pyright: ignore[reportUnknownMemberType]
                    name=name,
                    parent=self,
                    callobj=partial(_run_doctest, test),
                )
            )
        )


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command-line options for the stubtester plugin.

    Args:
        parser (pytest.Parser): Pytest command-line parser.

    """
    parser.addoption(
        COMMAND,
        action="store_true",
        default=False,
        help="Enable automatic .pyi file collection and doctest execution",
    )


@pytest.hookimpl(trylast=True)
def pytest_collect_file(
    file_path: Path,
    parent: pytest.Collector,
) -> PyiModule | None:
    """Collect .pyi files for doctest execution.

    Args:
        file_path (Path): Path to the file being collected.
        parent (pytest.Collector): Parent collector node.

    Returns:
        PyiModule | None: PyiModule instance if .pyi file and enabled, None otherwise.

    """
    if not parent.config.getoption(COMMAND) or file_path.suffix.lower() != ".pyi":
        return None

    return PyiModule.from_parent(parent=parent, path=file_path)  # pyright: ignore[reportUnknownMemberType]


def _recurse_extract(node: IsDef, prefix: str = "") -> Iterator[tuple[str, str, int]]:
    docstring = _get_doc(node)
    full_name = f"{prefix}{node.name}" if prefix else node.name

    if docstring.is_some():
        yield (full_name, docstring.unwrap(), node.lineno)
    if isinstance(node, ast.ClassDef):
        yield from (
            pc
            .Iter(node.body)
            .filter(_is_def)
            .flat_map(lambda n: _recurse_extract(n, f"{full_name}."))
        )


def _run_doctest(dtest: doctest.DocTest) -> None:
    runner = doctest.DocTestRunner()
    _ = runner.run(dtest)
    if runner.failures:
        failure_msgs = (
            pc
            .Iter(dtest.examples)
            .enumerate()
            .filter_star(lambda _, ex: ex.exc_msg is not None)
            .map_star(lambda _, ex: f"Line {ex.lineno}: {ex.source.strip()}")
            .join("\n")
        )
        pytest.fail(f"Doctest failed: {runner.failures} failures\n{failure_msgs}")


def _is_def(n: object) -> TypeIs[IsDef]:
    return isinstance(n, ast.FunctionDef | ast.ClassDef)


def _get_doc(node: ast.FunctionDef | ast.ClassDef | ast.Module) -> pc.Option[str]:
    return pc.Option(ast.get_docstring(node)).filter(lambda d: ">>>" in d)
