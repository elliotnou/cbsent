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

from cbsent.labels import STANCES, TOPICS

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


# Adapted from the benchmark's annotation guide: sentence-level monetary
# policy stance of FOMC communication.
TDW_BENCH_PROMPT = """\
You classify single sentences from FOMC communications (meeting minutes,
speeches, press conferences) by monetary policy stance. Answer with
exactly one of: hawkish, dovish, neutral.

- hawkish: the sentence indicates a tightening of monetary policy or an
  economic reading that supports tightening: rising or above-target
  inflation or inflation expectations, an overheating economy or labour
  market, rate increases, reduced accommodation or balance sheet runoff.
- dovish: the sentence indicates an easing of monetary policy or an
  economic reading that supports easing: falling or below-target
  inflation, economic weakness or slack, rate cuts, added accommodation
  or asset purchases.
- neutral: mixed or balanced readings, statements of fact with no
  directional implication for policy, or procedural/descriptive language.

Judge the sentence on its own. Respond with JSON: {"stance": "..."}"""


def _cache_key(model: str, sentence: str, system_prompt: str) -> str:
    payload = json.dumps({"m": model, "p": system_prompt, "s": sentence}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


# Labels loaded from the committed export, consulted before any API call so
# reported numbers can be reproduced without a key. Keyed by prompt as well
# as model and sentence: the codebook prompt and the benchmark prompt ask
# subtly different questions and must never answer for each other.
_PRIMED: dict = {}

PROMPT_NAMES = {"codebook": None, "tdw_bench": None}


def _prompt_name(system_prompt: str):
    if system_prompt == SYSTEM_PROMPT:
        return "codebook"
    if system_prompt == TDW_BENCH_PROMPT:
        return "tdw_bench"
    return None


def prime_from_csv(path: str) -> int:
    """Load exported labels so they are used instead of calling the API."""
    import csv

    if not os.path.exists(path):
        return 0
    loaded = 0
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stance, topic = row.get("stance"), row.get("topic")
            prompt = row.get("prompt", "codebook")
            if stance not in STANCES or prompt not in PROMPT_NAMES:
                continue
            if prompt == "codebook" and topic not in TOPICS:
                continue
            _PRIMED[(row["model"], prompt, row["sentence"])] = {
                "stance": stance,
                "topic": topic if topic in TOPICS else None,
            }
            loaded += 1
    return loaded


def label_many(sentences, model: str, cache_dir: str, workers: int = 32,
               progress_every: int = 200, **kwargs):
    """Label a list of sentences in parallel, returning one dict or None each.

    Order matches the input. Cached sentences cost nothing, so re-running
    is cheap and the same call can be used to top up a partial cache.
    Extra keyword arguments (system_prompt, require_topic) pass through to
    label_sentence.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = [None] * len(sentences)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(label_sentence, s, model, cache_dir, **kwargs): i
            for i, s in enumerate(sentences)
        }
        for future in as_completed(futures):
            i = futures[future]
            try:
                results[i] = future.result()
            except Exception as exc:
                print(f"  sentence {i} failed: {str(exc)[:100]}")
            done += 1
            if progress_every and done % progress_every == 0:
                print(f"  {done}/{len(sentences)} labelled...")
    return results


def label_sentence(sentence: str, model: str, cache_dir: str,
                   client=None, system_prompt: str = SYSTEM_PROMPT,
                   require_topic: bool = True) -> Optional[dict]:
    """Return {"stance": ..., "topic": ...} for one sentence, cached.

    A different system_prompt gets its own cache entries; benchmark
    prompts that classify stance only pass require_topic=False.
    """
    name = _prompt_name(system_prompt)
    if name is not None:
        primed = _PRIMED.get((model, name, sentence))
        if primed is not None:
            return primed

    key = _cache_key(model, sentence, system_prompt)
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
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": sentence},
        ],
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    parsed = json.loads(raw)

    stance = str(parsed.get("stance", "")).lower().strip()
    topic = str(parsed.get("topic", "")).lower().strip()
    if stance not in STANCES:
        return None
    if require_topic and topic not in TOPICS:
        return None

    label = {"stance": stance, "topic": topic if topic in TOPICS else None}
    # Usage is recorded because reasoning tokens are billed but never
    # appear in the response text, so cost cannot be reconstructed later.
    usage = {}
    if getattr(resp, "usage", None) is not None:
        usage = {
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
        }
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"model": model, "sentence": sentence, "label": label,
                   "raw": raw, "usage": usage}, f)
    return label
