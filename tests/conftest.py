"""Shared test fixtures for the profitability engine test suite."""

import os
import pytest

TEST_DB_PATH = "/tmp/profitability_test.db"


@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Remove test database before and after each test."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
