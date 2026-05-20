"""Configure pytest for stubtester plugin testing."""

pytest_plugins = ["pytester"]


def pytest_configure(config: object) -> None:
    """Enable stubtester plugin by default in tests."""
    # pyrefly: ignore [missing-attribute]
    config.option.pyi_enabled = True
