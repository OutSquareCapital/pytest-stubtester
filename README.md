# pytest-stubtester

A pytest plugin for testing doctests in `.pyi` stub files.

Designed for **Cython/PyO3/Rust extensions**, **third-party stubs**, or **stub-only packages**.

> 💡 For regular Python code, write doctests in `.py` files instead.

## 📦 Installation

```bash
uv add git+https://github.com/OutSquareCapital/pytest-stubtester.git
```

## 🚀 Quick Start

```bash
uv run pytest tests/ --stubs -v
```

### Command Examples

```bash
# Run all .pyi files
uv run pytest tests/ --stubs -v

# Test specific file
uv run pytest tests/my_stubs.pyi --stubs -v

# Test specific function
uv run pytest tests/my_stubs.pyi::function_name --stubs -v

# Run tests matching pattern
uv run pytest tests/my_stubs.pyi -k multiply --stubs -v
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

Create a `.pyi` file with doctests:

```python
# math_helpers.pyi
def add(a: int, b: int) -> int:
    """Add two numbers.

    >>> add(2, 3)
    5
    >>> add(-1, 1)
    0
    """


def multiply(a: int, b: int) -> int:
    """Multiply two numbers.

    >>> multiply(3, 4)
    12
    """
```

Run with pytest:

```bash
uv run pytest math_helpers.pyi --stubs -v
tests/math_helpers.pyi::add PASSED      [ 50%]
tests/math_helpers.pyi::multiply PASSED [100%]
```

### Dependencies

- Python 3.12>=
- [pyochain](https://github.com/OutSquareCapital/pyochain) for internal implementation
