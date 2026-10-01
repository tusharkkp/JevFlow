import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure repo root is on sys.path so "from backend.app..." works anywhere
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.app.core.config import settings
from backend.app.providers.registry import ProviderRegistry
from backend.app.providers.small_model_provider import SmallModelProvider
from backend.app.providers.frontier_model_provider import FrontierModelProvider
import backend.app.main as main_module
from backend.app.main import app


@pytest.fixture(autouse=True)
def isolate_test_environment(monkeypatch):
    """Ensure tests run offline with deterministic mock providers and clean cache."""
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", None)
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    # Reset main's shared provider_registry with simulated providers
    main_module.provider_registry = ProviderRegistry(
        small_model_provider=SmallModelProvider(simulated_latency_ms=0.0),
        frontier_model_provider=FrontierModelProvider(simulated_latency_ms=0.0),
    )
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
