"""Pytest plugin for discovering and running doctests from .pyi stub files."""

from __future__ import annotations

import ast
import doctest
import re
from typing import TYPE_CHECKING, TypeIs

import pytest
from pyochain import Iter, option

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from _pytest.doctest import DoctestModule
    from pyochain.abc import PyoIterator

type IsDef = ast.FunctionDef | ast.ClassDef
type HasDoc = IsDef | ast.Module
MARKDOWN_BLOCK = re.compile(r"```python\n(.*?)\n```", re.DOTALL)
"""Pattern to extract Python code blocks from Markdown-formatted docstrings.

Example:
    ```python
    >>> 1 + 1
    2
    ```
"""
type Parsed = tuple[str, str, int]
"""Parsed doctest information as a tuple of name (str), docstring (str), and line number (int)."""


def collect_all_tests(
    parent: DoctestModule, path: Path
) -> Iterator[pytest.DoctestItem]:

    txt = path.read_text(encoding="utf-8")
    filename = str(path)
    tree = ast.parse(txt, filename)
    return (
        _get_doc(tree, path.stem, 1)
        .chain(Iter(tree.body).filter(_is_def).flat_map(_extract_all_docs))
        .map_star(lambda name, doc, lineno: _to_doctest(name, doc, lineno, filename))
        .filter_star(lambda _, test: bool(test.examples))
        .map_star(
            lambda name, test: pytest.DoctestItem.from_parent(
                parent, name=name, runner=doctest.DebugRunner(), dtest=test
            ),
        )
    )


def _to_doctest(
    name: str, docstring: str, lineno: int, filename: str
) -> tuple[str, doctest.DocTest]:
    string = _parse_docstring(docstring)
    tst = doctest.DocTestParser().get_doctest(string, {}, name, filename, lineno)

    return name, tst


def _parse_docstring(docstring: str) -> str:
    return (
        Iter(MARKDOWN_BLOCK.findall(docstring))
        .then(lambda m: m.join("\n"))
        .unwrap_or(docstring)
    )


def _extract_all_docs(node: IsDef, prefix: str = "") -> PyoIterator[Parsed]:
    full_name = f"{prefix}{node.name}" if prefix else node.name
    match node:
        case ast.ClassDef():
            return _get_doc(node, full_name, node.lineno).chain(
                Iter(node.body)
                .filter(_is_def)
                .flat_map(lambda n: _extract_all_docs(n, f"{full_name}.")),
            )
        case ast.FunctionDef():
            return _get_doc(node, full_name, node.lineno)


def _get_doc(node: HasDoc, name: str, lineno: int) -> PyoIterator[Parsed]:
    return (
        option(ast.get_docstring(node))
        .filter(lambda d: ">>>" in d)
        .map(lambda doc: (name, doc, lineno))
        .iter()
    )


def _is_def(n: object) -> TypeIs[IsDef]:
    return isinstance(n, ast.FunctionDef | ast.ClassDef)
