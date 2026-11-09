import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    # Fail any accidental HTTP transport usage, including the real SDK.
    import httpx

    async def blocked(*args, **kwargs):
        raise AssertionError("Network access is forbidden in unit tests")

    monkeypatch.setattr(httpx.AsyncClient, "send", blocked)


@pytest.fixture
def project_data():
    return json.loads((Path(__file__).parent / "fixtures/website_project.json").read_text())


class FakeProvider:
    def __init__(self, output=None, error=None):
        self.output = output
        self.error = error
        self.calls = []

    async def generate(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        if self.output is not None:
            return self.output
        sources = json.loads(kwargs["user_prompt"])["wording_sources"]
        return json.dumps({"sections": [{"source_ref": k, "text": v} for k, v in sources.items()]})
