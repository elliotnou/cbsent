"""LLM-assisted labeling against the codebook.

Used for the bootstrap first pass (cheap model) and for the zero-shot
GPT-5 baseline (Phase 4). Every response is cached on disk keyed by
(model, prompt, sentence), so each sentence is billed once and every
reported number can be recomputed offline from the cache.
"""

import hashlib
import json
import os
from typing import Optional

STANCES = ("hawkish", "dovish", "neutral")
TOPICS = ("inflation", "employment", "growth", "financial_stability", "guidance")

SYSTEM_PROMPT = """\
You label single sentences from Federal Reserve and Bank of Canada
communications for monetary policy stance and topic.

Stance, exactly one of hawkish, dovish, neutral:
- hawkish: signals tighter policy or pressure toward it (hikes delivered or
  likely, inflation above target or risks tilted up, overheating economy,
  balance sheet runoff, restrictive-for-longer commitments).
- dovish: signals easier policy or pressure toward it (cuts delivered or
  likely, inflation returning to or below target, economic weakness or
  slack, asset purchases, keeping stimulus in place).
- neutral: process language, balanced risk talk, data recitation with no
  directional policy implication, mandate/voting boilerplate.

Rules:
1. Negation flips or voids the surface reading: "not yet appropriate to
   raise" is not hawkish; "does not anticipate reducing the rate until
   confident on inflation" is hawkish (restrictive for longer).
2. Hedges weaken but do not flip: "some further firming may be
   appropriate" is hawkish; pure optionality with no direction is neutral.
3. Judge the sentence alone; do not assume outside context.
4. Past policy actions carry their direction; "maintained the rate" is
   neutral absent directional guidance.

Topic, exactly one of inflation, employment, growth, financial_stability,
guidance. Pick the topic carrying the stance; for neutral sentences the
dominant subject. "guidance" covers the policy decision itself, forward
guidance, balance sheet policy, and voting.

Respond with JSON: {"stance": "...", "topic": "..."}"""


def _cache_key(model: str, sentence: str) -> str:
    payload = json.dumps({"m": model, "p": SYSTEM_PROMPT, "s": sentence}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def label_sentence(sentence: str, model: str, cache_dir: str,
                   client=None) -> Optional[dict]:
    """Return {"stance": ..., "topic": ...} for one sentence, cached."""
    key = _cache_key(model, sentence)
    path = os.path.join(cache_dir, key + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)["label"]

    if client is None:
        from openai import OpenAI
        client = OpenAI()

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": sentence},
        ],
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    parsed = json.loads(raw)

    stance = str(parsed.get("stance", "")).lower().strip()
    topic = str(parsed.get("topic", "")).lower().strip()
    if stance not in STANCES or topic not in TOPICS:
        return None

    label = {"stance": stance, "topic": topic}
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"model": model, "sentence": sentence, "label": label,
                   "raw": raw}, f)
    return label
