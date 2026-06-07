"""Optional LIVE ad-copy generation via Claude — with a stdlib template fallback.

Off by default and fully optional. A real call is attempted only when ALL of:
  * the `anthropic` SDK is installed   (pip install 'aion-populations[llm]')
  * ANTHROPIC_API_KEY is set in the env
  * AIONPOP_NO_LLM is NOT set
Otherwise every function degrades gracefully to the deterministic templates in
`gtm` — so the core package stays stdlib-only, offline, and CI-bulletproof.

  Model:  AIONPOP_LLM_MODEL  (default `claude-sonnet-4-6`; set `claude-opus-4-8`
          for maximum quality, `claude-haiku-4-5` for cheapest).

`enrich_ads_and_moves` is the one public entry point. It NEVER raises: on any
failure (no key, network error, malformed reply) it returns the originals it was
given, tagged `llm=False`, so the caller can always render *something*.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

DEFAULT_MODEL = "claude-sonnet-4-6"

_SYSTEM = (
    "You are an elite direct-response copywriter and B2B go-to-market strategist "
    "(Eugene Schwartz precision meets a top growth lead). You write concrete, "
    "specific, non-generic copy that respects the reader's intelligence. Ban hype "
    "words (unlock, elevate, revolutionize, game-changer, seamless, cutting-edge) "
    "and empty adjectives — every line must earn its place with a concrete benefit, "
    "proof, or hook. Write in the SAME LANGUAGE as the product pitch. "
    "Output ONLY a single valid JSON object — no prose, no markdown fences."
)


def model_name() -> str:
    return (os.environ.get("AIONPOP_LLM_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def available() -> bool:
    """True only if a real call could plausibly succeed (key + SDK + not disabled)."""
    if os.environ.get("AIONPOP_NO_LLM"):
        return False
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except Exception:
        return False
    return True


def _extract_json(text: str) -> Optional[dict]:
    """Pull the first JSON object out of a model reply (tolerates ```json fences)."""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        raw = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        raw = text[start:end + 1]
    try:
        obj = json.loads(raw)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _build_prompt(brief: dict, ads: List[dict], moves: List[str]) -> str:
    lines = [
        "Write live, ready-to-publish go-to-market copy.",
        "",
        f"PRODUCT: {brief.get('product', 'the product')}",
        f"MARKET/REGION: {brief.get('region', '')}",
        f"GOAL: {brief.get('goal', 'awareness')}",
        f"ONE-LINER: {brief.get('pitch', '')}",
        "",
        "Write one ad per WINNING MOVE below, in the SAME ORDER. For each, use that "
        "move's exact segment / channel / angle / offer / format — the copy must fit "
        "the channel's norms (e.g. LinkedIn ≠ cold email ≠ Google Search ad):",
        "",
    ]
    for i, a in enumerate(ads, 1):
        lines.append(
            f"  MOVE {i} — segment: {a.get('segment')} | channel: {a.get('channel')} | "
            f"angle: {a.get('angle')} | offer: {a.get('offer')} | format: {a.get('format')}"
        )
    lines += [
        "",
        "Also write 5–6 short STRATEGIC MOVES (plain language, each ≤ 22 words). In "
        "each, wrap the single most important lever in **double asterisks**. Make the "
        "last move about running these ads for real and feeding clicks/replies back to "
        "certify which truly work.",
        "",
        "Return ONLY this JSON (ads array same length & order as the moves above):",
        '{"ads":[{"headline":"≤12 words, punchy, channel-appropriate",'
        '"body":"1–2 concrete sentences tailored to the segment + angle",'
        '"cta":"action CTA matching the offer"}],'
        '"moves":["move with a **bold** lever", "..."]}',
    ]
    return "\n".join(lines)


def _merge_ads(ads: List[dict], generated) -> List[dict]:
    """Overlay LLM headline/body/cta onto each original ad, preserving its combo
    metadata, score, and id so the UI keeps working. Skips blanks."""
    if not isinstance(generated, list):
        return ads
    out: List[dict] = []
    for i, ad in enumerate(ads):
        g = generated[i] if i < len(generated) and isinstance(generated[i], dict) else {}
        merged = dict(ad)
        for k in ("headline", "body", "cta"):
            v = g.get(k)
            if isinstance(v, str) and v.strip():
                merged[k] = v.strip()
        out.append(merged)
    return out


def enrich_ads_and_moves(
    brief: dict, ads: List[dict], moves: List[str], *, timeout: float = 40.0
) -> Dict[str, object]:
    """Rewrite ad copy + strategic moves with Claude.

    Returns {"ads": [...], "moves": [...], "llm": bool, "model": str|None}.
    On ANY failure returns the originals with llm=False — never raises.
    """
    base: Dict[str, object] = {"ads": ads, "moves": moves, "llm": False, "model": None}
    if not ads or not available():
        return base
    try:
        import anthropic

        client = anthropic.Anthropic()
        try:                                   # per-request timeout (SDK version-safe)
            client = client.with_options(timeout=timeout)
        except Exception:
            pass
        msg = client.messages.create(
            model=model_name(),
            max_tokens=1600,
            temperature=0.7,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _build_prompt(brief, ads, moves)}],
        )
        text = "".join(
            getattr(b, "text", "") for b in msg.content
            if getattr(b, "type", None) == "text"
        )
        data = _extract_json(text)
        if not data:
            return base
        new_moves = data.get("moves")
        if isinstance(new_moves, list):
            cleaned = [str(m).strip() for m in new_moves if str(m).strip()]
            new_moves = cleaned or moves
        else:
            new_moves = moves
        return {
            "ads": _merge_ads(ads, data.get("ads")),
            "moves": new_moves,
            "llm": True,
            "model": model_name(),
        }
    except Exception:
        return base
