"""Tests for the mission-control dashboard routes (no network)."""
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from kudbee_quant.api import app  # noqa: E402

client = TestClient(app)


@pytest.mark.parametrize("path", ["/", "/dashboard"])
def test_dashboard_served_as_html(path):
    r = client.get(path)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "MISSION CONTROL" in r.text
    # The XSS guard must ship with the page: every server-derived string is
    # escaped client-side before innerHTML (journal text can arrive via the
    # alert webhook).
    assert "const esc =" in r.text


def test_dashboard_reads_real_journal_fields():
    # The /api/journal contract this page renders: scorecard rows expose
    # n/hits/total_r/net_total_r and the equity input is resolved_series[].r.
    # Guard against regressing to the field names the page was first written
    # against (n_resolved/n_wins), which don't exist.
    html = client.get("/").text
    assert "net_total_r" in html
    assert "resolved_series" in html
    assert "n_resolved" not in html
    assert "n_wins" not in html


def test_metrics_endpoint_shape():
    r = client.get("/api/metrics")
    assert r.status_code == 200
    body = r.json()
    try:
        import psutil  # noqa: F401
    except ImportError:
        assert body == {"error": "psutil not installed"}
        return
    assert {"cpu_pct", "mem_pct", "mem_used_gb", "mem_total_gb",
            "disk_pct", "disk_used_gb", "disk_total_gb"} <= set(body)
    assert 0.0 <= body["cpu_pct"] <= 100.0
    assert 0.0 <= body["mem_pct"] <= 100.0
