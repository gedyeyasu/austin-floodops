from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_service_worker_never_replays_action_drafts_or_caches_authenticated_api():
    source = (ROOT / "app" / "static" / "sw.js").read_text()
    assert "syncOfflineQueue" not in source
    assert "requires_reconfirmation" in source
    assert "event.request.headers.has('Authorization')" in source
    assert "url.pathname === '/api/heartbeat'" in source


def test_dashboard_does_not_invent_openshell_probe_result():
    source = (ROOT / "app" / "static" / "index.html").read_text()
    assert "deny exfiltration" not in source
    assert "Adversarial endpoint did not run an OpenShell gateway probe" in source


def test_dashboard_does_not_persist_bearer_tokens_or_load_unpinned_script_modules():
    source = (ROOT / "app" / "static" / "index.html").read_text()
    assert "localStorage" not in source
    assert "https://esm.sh/" not in source
    assert 'leaflet.js" integrity="sha256-' in source
