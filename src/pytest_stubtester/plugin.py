"""Pytest plugin for discovering and running doctests from .pyi stub files."""

from __future__ import annotations

import ast
import doctest
import re
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from typing import TypeIs, override

import pytest
from pyochain import Iter, Null, Option, Some, option

type IsDef = ast.FunctionDef | ast.ClassDef
COMMAND = "--stubs"
MARKDOWN_BLOCK = re.compile(r"```python\n(.*?)\n```")

type Parsed = tuple[str, str, int]
"""Parsed doctest information as a tuple of name (str), docstring (str), and line number (int)."""


class PyiModule(pytest.Module):
    """Custom pytest Module for collecting doctests from .pyi files."""

    @override
    def collect(self) -> Iterator[pytest.Item]:
        """Collect all doctests from the .pyi file.

        Returns:
            Iterator[pytest.Item]: An iterator of pytest items to be executed.

        """
        add_test = partial(pytest.Function.from_parent, self)
        return _collect_all_tests(self.path).map_star(
            lambda name, test: add_test(name=name, callobj=partial(_run_doctest, test))
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

    return PyiModule.from_parent(parent=parent, path=file_path)


def _collect_all_tests(path: Path) -> Iter[tuple[str, doctest.DocTest]]:
    def _extract_doctests_from_ast() -> Iter[Parsed]:
        txt = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(txt, filename=str(path))
        except SyntaxError:
            return Iter(())

        match _get_doc(tree):
            case Some(doc):
                module_tests = Iter.once((path.stem, doc, 1))
            case Null():
                module_tests: Iter[Parsed] = Iter(())

        # pyrefly: ignore [unbound-name]
        return module_tests.chain(
            # pyrefly: ignore [bad-argument-type]
            Iter(tree.body).filter(_is_def).flat_map(_extract_all_docs)
        )

    return (
        _extract_doctests_from_ast()
        .map_star(lambda name, doc, lineno: _to_doctest(name, doc, lineno, path))
        .filter_star(lambda _, test: bool(test.examples))
    )


def _to_doctest(
    name: str, docstring: str, lineno: int, path: Path
) -> tuple[str, doctest.DocTest]:
    tst = doctest.DocTestParser().get_doctest(
        _extract_markdown_code_blocks(docstring),
        globs={},
        name=name,
        filename=str(path),
        lineno=lineno,
    )

    return name, tst


def _extract_markdown_code_blocks(docstring: str) -> str:
    return (
        Iter(MARKDOWN_BLOCK.findall(docstring))
        .then(lambda m: m.join("\n"))
        .unwrap_or(docstring)
    )


def _extract_all_docs(node: IsDef, prefix: str = "") -> Iterator[Parsed]:
    docstring = _get_doc(node)
    full_name = f"{prefix}{node.name}" if prefix else node.name
    if docstring.is_some():
        yield (full_name, docstring.unwrap(), node.lineno)
    match node:
        case ast.ClassDef():
            yield from (
                Iter(node.body)
                .filter(_is_def)
                # pyrefly: ignore [bad-argument-type]
                .flat_map(lambda n: _extract_all_docs(n, f"{full_name}."))
            )
        case _:
            return


def _get_doc(node: ast.FunctionDef | ast.ClassDef | ast.Module) -> Option[str]:
    return option(ast.get_docstring(node)).filter(lambda d: ">>>" in d)


def _run_doctest(dtest: doctest.DocTest) -> None:
    runner = doctest.DocTestRunner()
    _ = runner.run(dtest)
    if runner.failures:
        failure_msgs = (
            Iter(dtest.examples)
            .enumerate()
            .filter_star(lambda _, ex: ex.exc_msg is not None)
            .map_star(lambda _, ex: f"Line {ex.lineno}: {ex.source.strip()}")
            .join("\n")
        )
        msg = f"Doctest failed: {runner.failures} failures\n{failure_msgs}"
        pytest.fail(msg)


def _is_def(n: object) -> TypeIs[IsDef]:
    return isinstance(n, ast.FunctionDef | ast.ClassDef)
