"""Pytest plugin for discovering and running doctests from .pyi stub files."""

from __future__ import annotations

import ast
import doctest
import re
from typing import TYPE_CHECKING, TypeIs, override

import pytest
from _pytest.doctest import DoctestModule  # noqa: PLC2701
from pyochain import Err, Iter, Ok, Result, option

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pyochain.abc import PyoIterator
type IsDef = ast.FunctionDef | ast.ClassDef
type HasDoc = IsDef | ast.Module
COMMAND = "--stubs"
MARKDOWN_BLOCK = re.compile(r"```python\n(.*?)\n```")
"""Pattern to extract Python code blocks from Markdown-formatted docstrings.

Example:
    ```python
    >>> 1 + 1
    2
    ```
"""
type Parsed = tuple[str, str, int]
"""Parsed doctest information as a tuple of name (str), docstring (str), and line number (int)."""


class PyiModule(DoctestModule):
    """Custom pytest Module for collecting doctests from .pyi files."""

    @override
    def collect(self) -> Iterator[pytest.DoctestItem]:
        txt = self.path.read_text(encoding="utf-8")
        filename = str(self.path)
        return (
            _try_get_tree(txt, filename)
            .map(
                lambda tree: (
                    _get_doc(tree, self.path.stem, 1)
                    .chain(Iter(tree.body).filter(_is_def).flat_map(_extract_all_docs))
                    .map_star(
                        lambda name, doc, lineno: _to_doctest(
                            name, doc, lineno, filename
                        )
                    )
                    .filter_star(lambda _, test: bool(test.examples))
                    .map_star(
                        lambda name, test: pytest.DoctestItem.from_parent(
                            self, name=name, runner=doctest.DebugRunner(), dtest=test
                        )
                    )
                )
            )
            .unwrap()
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
def pytest_collect_file(file_path: Path, parent: pytest.Collector) -> PyiModule | None:
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


def _try_get_tree(txt: str, filename: str) -> Result[ast.Module, SyntaxError]:
    try:
        return Ok(ast.parse(txt, filename))

    except SyntaxError as e:
        return Err(e)


def _to_doctest(
    name: str, docstring: str, lineno: int, filename: str
) -> tuple[str, doctest.DocTest]:
    string = (
        Iter(MARKDOWN_BLOCK.findall(docstring))
        .then(lambda m: m.join("\n"))
        .unwrap_or(docstring)
    )
    tst = doctest.DocTestParser().get_doctest(string, {}, name, filename, lineno)

    return name, tst


def _extract_all_docs(node: IsDef, prefix: str = "") -> PyoIterator[Parsed]:
    full_name = f"{prefix}{node.name}" if prefix else node.name
    match _get_doc(node, full_name, node.lineno):
        case ast.ClassDef() as class_node:
            return class_node.chain(
                Iter(node.body)
                .filter(_is_def)
                .flat_map(lambda n: _extract_all_docs(n, f"{full_name}."))
            )
        case _ as def_node:
            return def_node


def _get_doc(node: HasDoc, name: str, lineno: int) -> PyoIterator[Parsed]:
    return (
        option(ast.get_docstring(node))
        .filter(lambda d: ">>>" in d)
        .map(lambda doc: (name, doc, lineno))
        .iter()
    )


def _is_def(n: object) -> TypeIs[IsDef]:
    return isinstance(n, ast.FunctionDef | ast.ClassDef)
