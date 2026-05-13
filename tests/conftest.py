import pytest
from pathlib import Path


@pytest.fixture
def vault_path(tmp_path):
    return tmp_path
