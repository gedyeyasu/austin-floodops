import sys
from types import SimpleNamespace

import pytest

from app.security.hiddenlayer import HiddenLayerUnavailable, evaluate_interaction_v2


@pytest.mark.asyncio
async def test_hiddenlayer_auth_failure_is_actionable_and_redacts_provider_response(monkeypatch):
    exposed_client_identifier = "client-identifier-must-not-reach-the-operator"

    class RejectingRuntime:
        def evaluate_interaction(self, **_kwargs):
            raise RuntimeError(
                f"Error code: 401 - invalid_client for {exposed_client_identifier}"
            )

    class RejectingHiddenLayer:
        def __init__(self, **_kwargs):
            self.runtime = RejectingRuntime()

    monkeypatch.setitem(
        sys.modules,
        "hiddenlayer",
        SimpleNamespace(HiddenLayer=RejectingHiddenLayer),
    )

    with pytest.raises(HiddenLayerUnavailable) as raised:
        await evaluate_interaction_v2(
            client_id="expired-client",
            client_secret="expired-secret",
            interaction={"model": "test", "messages": [{"role": "user", "content": "safe"}]},
        )

    message = str(raised.value)
    assert "authentication failed" in message
    assert "expire after 72 hours" in message
    assert exposed_client_identifier not in message
