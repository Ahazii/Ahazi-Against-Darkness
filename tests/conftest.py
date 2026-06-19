"""Shared pytest fixtures for API tests that touch DATA_DIR or game.db."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import load_settings
from app.db import Store, init_db
from app.engine.adventure_import import seed_bundled_adventures


@pytest.fixture
def isolated_app_env(monkeypatch, tmp_path):
    """Per-test DATA_DIR + store so API tests do not share .data/game.db."""
    data_dir = tmp_path / "appdata"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    settings = load_settings()
    monkeypatch.setattr(main, "settings", settings)
    init_db(settings.db_path)
    store = Store(settings.db_path)
    monkeypatch.setattr(main, "store", store)
    seed_bundled_adventures(settings.root_dir, settings.data_dir)
    return settings


@pytest.fixture
def client(isolated_app_env) -> TestClient:
    return TestClient(main.app)
