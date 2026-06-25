# pytest-stubtester

A pytest plugin for testing doctests in `.pyi` stub files.

Designed for **Cython/PyO3/Rust extensions** or **stub-only packages**.

> 💡 For regular Python code, write doctests in `.py` files instead.

## 📦 Installation

```bash
uv add git+https://github.com/OutSquareCapital/pytest-stubtester.git
```

## 🚀 Quick Start

```bash
uv run pytest <path_to_tests> --stubs
```

### Auto-Enable

**Via `pyproject.toml`:**

```toml
[tool.pytest.ini_options]
addopts = ["--stubs"]
```

**Via `conftest.py`:**

```python
def pytest_configure(config: object) -> None:
    config.option.pyi_enabled = True  # type: ignore[attr-defined]
```

## 📝 Example

Create a `foo.pyi` file with doctests:

```python
def add(a: int, b: int) -> int:
    """Add two numbers.

    >>> from operator import add
    >>> add(2, 3)
    5
    >>> add(-1, 1)
    0
    """

# Also works with markup code blocks:
def multiply(a: int, b: int) -> int:
    """Multiply two numbers.

    ```python
    >>> from operator import mul
    >>> mul(3, 4)
    12

    ```
    """

```

Run with pytest:

```bash
uv run pytest foo.pyi --stubs -v
```

Output:

```shell
foo.pyi::add PASSED      [ 50%]
foo.pyi::multiply PASSED [100%]
```

### Dependencies

- Python 3.13>=
- [pyochain](https://github.com/OutSquareCapital/pyochain) for internal implementation
