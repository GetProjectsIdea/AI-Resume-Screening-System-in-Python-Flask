import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3"),
                       "SECRET_KEY": "test"})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sample_dir():
    return ROOT / "sample_data"
