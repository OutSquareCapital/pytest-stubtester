"""Pytest plugin for discovering and running doctests from .pyi stub files."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import pytest
from _pytest.doctest import DoctestModule  # noqa: PLC2701

from ._collect import collect_all_tests

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

COMMAND = "--stubs"


class PyiModule(DoctestModule):
    """Custom pytest Module for collecting doctests from .pyi files."""

    @override
    def collect(self) -> Iterator[pytest.DoctestItem]:
        return collect_all_tests(self, self.path)


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
