"""
Shared pytest config.

The async API tests in test_diagnostics.py declare an async fixture but rely
on pytest-asyncio's auto mode to drive it. Set that here so individual files
don't need to repeat marker boilerplate.
"""
import pytest


def pytest_collection_modifyitems(config, items):
    # Mark async tests automatically.
    for item in items:
        if item.get_closest_marker("asyncio"):
            continue
        if item.function.__code__.co_flags & 0x100:  # CO_COROUTINE
            item.add_marker(pytest.mark.asyncio)
