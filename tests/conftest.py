from pathlib import Path
from shutil import rmtree

import pytest


@pytest.fixture(scope="class")
def setup_teardown_dir():
    """Fixture to create and remove the temporary test directory."""
    test_path = Path("test_reports")
    test_path.mkdir(exist_ok=True)
    yield
    rmtree("test_reports")
