"""Server-side AI chart review — an OpenAI vision read of an uploaded chart image.

Isolated by design: this module NEVER imports the execution layer and NEVER
places an order. It turns a single chart screenshot into a structured, HONEST,
falsifiable read (bias / setup / confidence / key levels / suggested bracket /
recommendation) that the operator can act on manually. The OpenAI key is passed
in by the caller (read via ``config.secrets.get_secret`` in the API) and is never
logged here.

The ``client`` argument is injectable so tests can drive the parser/validator
without a network call or the ``openai`` package installed.
"""
from __future__ import annotations

import base64
import json

DEFAULT_MODEL = "gpt-4o"

# Accepted upload content types -> file extension used for on-disk storage.
ALLOWED_CONTENT_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}

_BIAS = {"long", "short", "neutral"}
_RECOMMENDATION = {"trade_candidate", "watch", "no_trade"}

_SYSTEM_PROMPT = (
    "You are a disciplined trading-chart analyst working inside a quant research "
    "tool. You read a single chart screenshot and return a structured, honest, "
    "falsifiable assessment. You never guarantee outcomes. If the chart is unclear "
    "or shows no edge, say so with low confidence and final_recommendation "
    "'no_trade'. Respond with ONLY a JSON object matching the requested schema."
)


class ChartReviewError(Exception):
    """Raised when the vision model returns a missing/unparseable structured read."""


def _build_user_prompt(symbol: str, timeframe: str, notes: str) -> str:
    parts = [f"Symbol: {symbol or 'unknown'}", f"Timeframe: {timeframe or 'unknown'}"]
    if notes:
        parts.append(f"Trader notes: {notes}")
    parts.append(
        "Analyze the attached chart. Return a JSON object with EXACTLY these keys: "
        "bias (one of 'long','short','neutral'), setup_name (short string), "
        "confidence (integer 0-100), key_levels (object with 'support' and "
        "'resistance' arrays of numbers), suggested_entry (number or null), "
        "suggested_stop (number or null), suggested_target (number or null), "
        "rationale (string, <= 100 words), final_recommendation (one of "
        "'trade_candidate','watch','no_trade')."
    )
    return "\n".join(parts)


def _opt_num(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _nums(seq) -> list[float]:
    out: list[float] = []
    for v in seq or []:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def _coerce(raw) -> dict:
    """Validate + normalize the model's JSON into the strict schema. Raises
    :class:`ChartReviewError` on anything missing or out of range."""
    if not isinstance(raw, dict):
        raise ChartReviewError("model did not return a JSON object")
    bias = str(raw.get("bias", "")).strip().lower()
    if bias not in _BIAS:
        raise ChartReviewError(f"invalid bias: {raw.get('bias')!r}")
    rec = str(raw.get("final_recommendation", "")).strip().lower()
    if rec not in _RECOMMENDATION:
        raise ChartReviewError(
            f"invalid final_recommendation: {raw.get('final_recommendation')!r}")
    try:
        confidence = int(round(float(raw.get("confidence"))))
    except (TypeError, ValueError):
        raise ChartReviewError("confidence must be a number") from None
    confidence = max(0, min(100, confidence))
    levels = raw.get("key_levels")
    if not isinstance(levels, dict):
        levels = {}
    return {
        "bias": bias,
        "setup_name": (str(raw.get("setup_name") or "").strip()[:120]) or "unspecified",
        "confidence": confidence,
        "key_levels": {
            "support": _nums(levels.get("support")),
            "resistance": _nums(levels.get("resistance")),
        },
        "suggested_entry": _opt_num(raw.get("suggested_entry")),
        "suggested_stop": _opt_num(raw.get("suggested_stop")),
        "suggested_target": _opt_num(raw.get("suggested_target")),
        "rationale": str(raw.get("rationale") or "").strip()[:1000],
        "final_recommendation": rec,
    }


def review_chart(image_bytes: bytes, content_type: str, symbol: str,
                 timeframe: str = "", notes: str = "", *,
                 api_key: str, model: str = DEFAULT_MODEL, client=None) -> dict:
    """Call OpenAI vision on the chart and return a validated structured dict.

    ``client`` is injectable for tests; in production a lazily-imported OpenAI
    client is built from ``api_key``. Raises :class:`ChartReviewError` on an
    unsupported type or a malformed model read.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ChartReviewError(f"unsupported content type: {content_type}")
    if client is None:
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover - dependency guard
            raise ChartReviewError("openai package is not installed") from e
        client = OpenAI(api_key=api_key)

    data_url = f"data:{content_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": _build_user_prompt(symbol, timeframe, notes)},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]},
        ],
    )
    try:
        content = resp.choices[0].message.content
    except (AttributeError, IndexError) as e:
        raise ChartReviewError("empty response from model") from e
    try:
        raw = json.loads(content)
    except (TypeError, ValueError) as e:
        raise ChartReviewError("model response was not valid JSON") from e
    return _coerce(raw)
