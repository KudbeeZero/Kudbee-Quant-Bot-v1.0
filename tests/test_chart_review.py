"""Tests for the AI chart-review feature.

No network: the OpenAI vision call is mocked (the endpoint calls
``chart_review.review_chart``, which we monkeypatch). Storage is redirected to a
tmp dir via ``monkeypatch.chdir`` since the journal uses ``data/...`` relative to
the working directory. The live-execution path is never touched.
"""
import base64
import json

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("multipart")  # python-multipart: needed to parse the upload
from fastapi.testclient import TestClient  # noqa: E402

from kudbee_quant import api, chart_review  # noqa: E402
from kudbee_quant.api_auth import COOKIE_NAME, issue_session  # noqa: E402
from kudbee_quant.api_security import _reset_rate_limits  # noqa: E402

# Minimal PNG-ish payload — content isn't inspected (the model is mocked).
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

GOOD_REVIEW = {
    "bias": "long", "setup_name": "double_bottom", "confidence": 72,
    "key_levels": {"support": [100.0], "resistance": [110.0]},
    "suggested_entry": 101.0, "suggested_stop": 99.0, "suggested_target": 107.0,
    "rationale": "neckline break with vector confirm",
    "final_recommendation": "trade_candidate",
}


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    _reset_rate_limits()
    monkeypatch.chdir(tmp_path)   # data/chart_reviews.json + data/chart_images/ land here
    yield


def _auth_client(monkeypatch):
    monkeypatch.setenv("KUDBEE_SESSION_SECRET", "test-secret")
    c = TestClient(api.app)
    c.cookies.set(COOKIE_NAME, issue_session())
    return c


def _enable(monkeypatch, key="sk-test"):
    monkeypatch.setenv("ENABLE_AI_CHART_REVIEW", "true")
    if key is None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENAI_API_KEY", key)


def _files(content_type="image/png", data=PNG):
    return {"image": ("chart.png", data, content_type)}


# --- gating ------------------------------------------------------------------

def test_requires_session(monkeypatch):
    _enable(monkeypatch)
    c = TestClient(api.app)  # no cookie
    assert c.post("/api/chart-review", files=_files(),
                  data={"symbol": "BTCUSDT"}).status_code == 401
    assert c.get("/api/chart-reviews").status_code == 401
    assert c.get("/api/chart-images/abcd1234").status_code == 401


def test_disabled_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_AI_CHART_REVIEW", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    c = _auth_client(monkeypatch)
    r = c.post("/api/chart-review", files=_files(), data={"symbol": "BTCUSDT"})
    assert r.status_code == 503


def test_disabled_without_api_key(monkeypatch):
    _enable(monkeypatch, key=None)
    c = _auth_client(monkeypatch)
    r = c.post("/api/chart-review", files=_files(), data={"symbol": "BTCUSDT"})
    assert r.status_code == 503


# --- input validation --------------------------------------------------------

def test_rejects_non_image(monkeypatch):
    _enable(monkeypatch)
    c = _auth_client(monkeypatch)
    r = c.post("/api/chart-review",
               files={"image": ("x.txt", b"hello", "text/plain")},
               data={"symbol": "BTCUSDT"})
    assert r.status_code == 415


def test_rejects_oversize(monkeypatch):
    _enable(monkeypatch)
    c = _auth_client(monkeypatch)
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (5 * 1024 * 1024 + 1)
    r = c.post("/api/chart-review", files=_files(data=big), data={"symbol": "BTCUSDT"})
    assert r.status_code == 413


def test_rejects_empty(monkeypatch):
    _enable(monkeypatch)
    c = _auth_client(monkeypatch)
    r = c.post("/api/chart-review", files=_files(data=b""), data={"symbol": "BTCUSDT"})
    assert r.status_code == 422


# --- happy path + persistence ------------------------------------------------

def test_happy_path_persists(monkeypatch, tmp_path):
    _enable(monkeypatch)
    monkeypatch.setattr(chart_review, "review_chart", lambda *a, **k: dict(GOOD_REVIEW))
    c = _auth_client(monkeypatch)
    r = c.post("/api/chart-review", files=_files(),
               data={"symbol": "btcusdt", "timeframe": "1h", "notes": "test"})
    assert r.status_code == 200
    body = r.json()
    assert body["review"]["bias"] == "long"
    assert body["symbol"] == "BTCUSDT"        # normalized by safe_symbol
    assert body["image_sha256"].startswith("sha256:")

    rec_path = tmp_path / "data" / "chart_reviews.json"
    assert rec_path.exists()
    saved = json.loads(rec_path.read_text())
    assert len(saved) == 1 and saved[0]["bias"] == "long"

    imgs = list((tmp_path / "data" / "chart_images").glob("*.png"))
    assert len(imgs) == 1

    lst = c.get("/api/chart-reviews").json()
    assert lst["reviews"][0]["symbol"] == "BTCUSDT"

    img = c.get(f"/api/chart-images/{body['id']}")
    assert img.status_code == 200 and img.headers["content-type"].startswith("image/")


def test_malformed_model_response(monkeypatch):
    _enable(monkeypatch)

    def boom(*a, **k):
        raise chart_review.ChartReviewError("bad json")

    monkeypatch.setattr(chart_review, "review_chart", boom)
    c = _auth_client(monkeypatch)
    r = c.post("/api/chart-review", files=_files(), data={"symbol": "BTCUSDT"})
    assert r.status_code == 502


# --- security ----------------------------------------------------------------

def test_no_key_or_raw_bytes_leak(monkeypatch, tmp_path):
    _enable(monkeypatch, key="sk-supersecret")
    monkeypatch.setattr(chart_review, "review_chart", lambda *a, **k: dict(GOOD_REVIEW))
    c = _auth_client(monkeypatch)
    r = c.post("/api/chart-review", files=_files(), data={"symbol": "BTCUSDT"})
    assert r.status_code == 200
    assert "sk-supersecret" not in r.text

    raw = (tmp_path / "data" / "chart_reviews.json").read_text()
    assert "sk-supersecret" not in raw
    # raw image bytes (as base64) are never serialized into the record — hash only.
    assert base64.b64encode(PNG).decode() not in raw
    rec = json.loads(raw)[0]
    assert rec["image_sha256"].startswith("sha256:") and rec["image_size_bytes"] == len(PNG)
    assert "image_bytes" not in rec


def test_chart_image_id_guard(monkeypatch):
    _enable(monkeypatch)
    c = _auth_client(monkeypatch)
    assert c.get("/api/chart-images/zzzzzzzz").status_code == 422  # well-formed length, non-hex
    assert c.get("/api/chart-images/abcd1234").status_code == 404  # valid hex, unknown id


# --- unit: review_chart parsing/validation (fake client, no network) ---------

class _FakeOpenAI:
    """Stands in for openai.OpenAI: client.chat.completions.create(...).choices[0].message.content."""

    def __init__(self, content):
        self._content = content
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        msg = type("M", (), {"content": self._content})
        choice = type("C", (), {"message": msg})
        return type("R", (), {"choices": [choice]})


def test_review_chart_with_fake_client():
    out = chart_review.review_chart(PNG, "image/png", "BTCUSDT", "1h",
                                    api_key="x", client=_FakeOpenAI(json.dumps(GOOD_REVIEW)))
    assert out["bias"] == "long" and out["confidence"] == 72
    assert out["final_recommendation"] == "trade_candidate"


def test_review_chart_malformed_json_raises():
    with pytest.raises(chart_review.ChartReviewError):
        chart_review.review_chart(PNG, "image/png", "BTC",
                                  api_key="x", client=_FakeOpenAI("not json"))


def test_coerce_clamps_and_rejects():
    out = chart_review._coerce({**GOOD_REVIEW, "confidence": 250})
    assert out["confidence"] == 100
    with pytest.raises(chart_review.ChartReviewError):
        chart_review._coerce({**GOOD_REVIEW, "bias": "sideways"})
    with pytest.raises(chart_review.ChartReviewError):
        chart_review._coerce({**GOOD_REVIEW, "final_recommendation": "yolo"})
