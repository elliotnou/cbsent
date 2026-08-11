"""Point-in-time event study: divergence index vs USD/CAD around decisions.

For each scheduled decision in the held-out window:
  1. Score every sentence published strictly before the release timestamp
     with the fine-tuned model.
  2. Compute the Fed-minus-BoC divergence index as of that instant, and
     its change since the previous scheduled decision by either bank, so
     the change captures only text published between the two releases.
  3. Measure the USD/CAD move from the release timestamp to a fixed
     horizon after it, intraday when tick data exists, else the change to
     the next daily rate.
  4. Report, for decisions flagged as surprises in data/decisions.csv,
     whether the index moved in the same direction as the pair.

The index only ever reads text with published_at < the release timestamp,
which the schema enforces by carrying the timestamp on every sentence row.

Usage:
    python scripts/event_study.py [--eval-start 2025-08-01] [--eval-end 2026-08-01]
                                  [--horizon-minutes 60] [--chart docs/divergence.png]
"""

import argparse
import csv
import datetime
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cbsent import fx
from cbsent.divergence import ScoredSentence, divergence, series
from cbsent.ingest import db
from cbsent.model import Scorer

UTC = datetime.timezone.utc
FX_CACHE = "data/fx_cache"
DECISIONS_CSV = "data/decisions.csv"
SCORE_CACHE = "data/score_cache.json"


def load_scored_sentences(conn, scorer: Scorer, upto: datetime.datetime,
                          cache_path: Optional[str] = None) -> List[ScoredSentence]:
    """Score every sentence published before `upto`.

    Scoring the whole corpus takes minutes on CPU, so results are cached
    per (model directory, device). The cache is keyed by sentence text and
    is only read when the model fingerprint matches.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.text, s.published_at, d.bank
            FROM sentences s JOIN documents d ON s.document_id = d.id
            WHERE s.published_at < %s
            ORDER BY s.published_at, s.id
            """,
            (upto,),
        )
        rows = cur.fetchall()

    texts = [r[0] for r in rows]
    fingerprint = scorer.fingerprint()
    cached = {}
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            blob = json.load(f)
        if blob.get("fingerprint") == fingerprint:
            cached = blob.get("scores", {})

    missing = [t for t in texts if t not in cached]
    if missing:
        print(f"scoring {len(missing)} sentences ({len(cached)} from cache)")
        for text, out in zip(missing, scorer.score_sentences(missing)):
            cached[text] = [out["score"], out["topic"]]
        if cache_path:
            os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"fingerprint": fingerprint, "scores": cached}, f)
    else:
        print(f"scoring skipped, all {len(texts)} sentences cached")

    return [
        ScoredSentence(published_at=row[1], bank=row[2],
                       score=cached[row[0]][0], topic=cached[row[0]][1])
        for row in rows
    ]


def load_decisions(path: str, start: datetime.date, end: datetime.date) -> List[dict]:
    if not os.path.exists(path):
        raise SystemExit(f"{path} not found; it lists the scheduled decisions and consensus")
    out = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            day = datetime.date.fromisoformat(row["decision_date"])
            if not (start <= day < end):
                continue
            row["decision_date"] = day
            row["release_ts"] = datetime.datetime.fromisoformat(row["release_ts_utc"]).replace(tzinfo=UTC)
            row["actual_bps"] = int(row["actual_bps"]) if row["actual_bps"] else None
            row["consensus_bps"] = int(row["consensus_bps"]) if row["consensus_bps"] else None
            out.append(row)
    out.sort(key=lambda r: r["release_ts"])
    return out


def fx_move(release_ts: datetime.datetime, horizon_minutes: int,
            daily: Dict[datetime.date, float]) -> tuple:
    """USD/CAD move after a release. Returns (move_pct, basis)."""
    try:
        ticks = fx.fetch_window(release_ts.astimezone(UTC).replace(tzinfo=None),
                                5, horizon_minutes, FX_CACHE)
    except Exception as exc:
        print(f"  intraday unavailable ({exc})")
        ticks = []

    naive_release = release_ts.astimezone(UTC).replace(tzinfo=None)
    before = [px for ts, px in ticks if ts <= naive_release]
    after = [px for ts, px in ticks if ts > naive_release]
    if before and after:
        return (after[-1] - before[-1]) / before[-1] * 100.0, "intraday"

    day = release_ts.astimezone(UTC).date()
    days = sorted(daily)
    prior = [d for d in days if d < day]
    later = [d for d in days if d >= day]
    if prior and later:
        return (daily[later[0]] - daily[prior[-1]]) / daily[prior[-1]] * 100.0, "daily"
    return None, "unavailable"


def coin_flip_note(hits: int, total: int) -> str:
    """Describe a hit count against a fair-coin null, two-sided."""
    if total == 0:
        return "no observations"
    from math import comb

    def tail(k):
        return sum(comb(total, i) for i in range(k, total + 1)) / 2 ** total

    lower = min(hits, total - hits)
    p = 2 * tail(total - lower)
    p = min(1.0, p)
    verdict = "not distinguishable from chance" if p > 0.10 else "unlikely under a fair coin"
    return f"two-sided binomial p = {p:.3f} against a fair coin, {verdict}"


def render_chart(div_series: Dict[datetime.date, float], daily: Dict[datetime.date, float],
                 decisions: List[dict], path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    days = sorted(div_series)
    if not days:
        print("no divergence series to chart")
        return
    fx_days = [d for d in days if d in daily]

    fig, ax1 = plt.subplots(figsize=(11, 5.5))
    # The index is piecewise constant: it only moves when a document is
    # published, so a step plot is the honest shape for it.
    div_line, = ax1.step(days, [div_series[d] for d in days], where="post",
                         color="#1f4e79", linewidth=1.6,
                         label="Fed minus BoC divergence index (left)")
    ax1.set_ylabel("Divergence index (hawkishness)", color="#1f4e79")
    ax1.tick_params(axis="y", labelcolor="#1f4e79")
    ax1.axhline(0.0, color="#999999", linewidth=0.8, linestyle=":")

    ax2 = ax1.twinx()
    fx_line, = ax2.plot(fx_days, [daily[d] for d in fx_days], color="#a63603",
                        linewidth=1.4, label="USD/CAD daily rate (right)")
    ax2.set_ylabel("USD/CAD", color="#a63603")
    ax2.tick_params(axis="y", labelcolor="#a63603")

    handles = [div_line, fx_line]
    for i, dec in enumerate(decisions):
        line = ax1.axvline(dec["decision_date"], color="#bbbbbb", linewidth=0.7,
                           alpha=0.8,
                           label="scheduled rate decision" if i == 0 else None)
        if i == 0:
            handles.append(line)
    surprises = [d for d in decisions if d.get("is_surprise") == "yes"]
    for i, dec in enumerate(surprises):
        line = ax1.axvline(dec["decision_date"], color="#c00000", linewidth=1.1,
                           alpha=0.9,
                           label="consensus surprise" if i == 0 else None)
        if i == 0:
            handles.append(line)

    subtitle = (f"{len(surprises)} of {len(decisions)} decisions differed from consensus"
                if surprises else
                "every decision in this window matched the economist consensus")
    ax1.set_title("Fed minus BoC policy divergence and USD/CAD, held-out period\n"
                  + subtitle)
    ax1.set_xlabel("Date")
    ax1.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.95)
    fig.autofmt_xdate()
    fig.tight_layout()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, dpi=160)
    print(f"chart written to {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-start", default="2025-08-01")
    parser.add_argument("--eval-end", default="2026-08-01")
    parser.add_argument("--model-dir", default="export/cbsent")
    parser.add_argument("--horizon-minutes", type=int, default=60)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--chart", default="docs/divergence.png")
    parser.add_argument("--score-cache", default=SCORE_CACHE)
    parser.add_argument("--no-results-append", action="store_true")
    args = parser.parse_args()

    start = datetime.date.fromisoformat(args.eval_start)
    end = datetime.date.fromisoformat(args.eval_end)
    decisions = load_decisions(DECISIONS_CSV, start, end)
    print(f"decisions in window: {len(decisions)}")

    scorer = Scorer(args.model_dir, device=args.device)
    horizon_end = datetime.datetime.combine(end, datetime.time(), tzinfo=UTC)
    with db.connect() as conn:
        sentences = load_scored_sentences(conn, scorer, horizon_end,
                                          cache_path=args.score_cache)
    print(f"scored sentences available: {len(sentences)}")

    daily = fx.fetch_daily_rates(FX_CACHE, start - datetime.timedelta(days=10), end)

    rows = []
    prev_div: Optional[float] = None
    for dec in decisions:
        div_now = divergence(sentences, dec["release_ts"])
        if div_now is None:
            print(f"  {dec['decision_date']} {dec['bank']}: index undefined, skipped")
            continue
        div_change = None if prev_div is None else div_now - prev_div
        move, basis = fx_move(dec["release_ts"], args.horizon_minutes, daily)
        rows.append({
            "date": dec["decision_date"], "bank": dec["bank"],
            "actual_bps": dec["actual_bps"], "consensus_bps": dec["consensus_bps"],
            "is_surprise": dec.get("is_surprise", ""),
            "divergence": div_now, "divergence_change": div_change,
            "fx_move_pct": move, "fx_basis": basis,
        })
        prev_div = div_now

    print(f"\n{'date':<12}{'bank':<6}{'act':>5}{'cons':>6}{'surp':>6}"
          f"{'index':>9}{'d_index':>9}{'fx %':>8}  basis")
    for r in rows:
        dc = f"{r['divergence_change']:+.4f}" if r["divergence_change"] is not None else "n/a"
        fm = f"{r['fx_move_pct']:+.3f}" if r["fx_move_pct"] is not None else "n/a"
        print(f"{str(r['date']):<12}{r['bank']:<6}"
              f"{'' if r['actual_bps'] is None else r['actual_bps']:>5}"
              f"{'' if r['consensus_bps'] is None else r['consensus_bps']:>6}"
              f"{r['is_surprise']:>6}{r['divergence']:>9.4f}{dc:>9}{fm:>8}  {r['fx_basis']}")

    # Directional agreement: a widening Fed-BoC gap ahead of the decision
    # should coincide with USD strength against CAD after the release.
    def agreement(subset):
        hits = [r for r in subset
                if (r["divergence_change"] > 0) == (r["fx_move_pct"] > 0)]
        return len(hits), len(subset)

    usable = [r for r in rows
              if r["divergence_change"] is not None and r["fx_move_pct"] is not None]
    surprises = [r for r in usable if r["is_surprise"] == "yes"]
    n_s, m_s = agreement(surprises)
    n_a, m_a = agreement(usable)
    bases = sorted({r["fx_basis"] for r in usable})

    if m_s:
        summary = (f"index moved directionally ahead of the pair on {n_s} of "
                   f"{m_s} surprises ({coin_flip_note(n_s, m_s)})")
    else:
        summary = (
            f"no consensus surprises occurred in this window: every scheduled "
            f"decision matched the economist consensus recorded in "
            f"{DECISIONS_CSV}. Across all {m_a} scheduled decisions, the index "
            f"moved directionally ahead of the pair on {n_a} of {m_a} "
            f"({coin_flip_note(n_a, m_a)})."
        )
    print(f"\n{summary}")

    os.makedirs("data", exist_ok=True)
    with open("data/event_study.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["date"])
        w.writeheader()
        w.writerows(rows)

    div_series = series(sentences, start, min(end, datetime.date.today()))
    render_chart(div_series, daily, decisions, args.chart)

    if not args.no_results_append:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        entry = (
            f"\n## Event study, {args.eval_start} to {args.eval_end}"
            f" ({datetime.date.today().isoformat()})\n\n"
            f"- command: `python scripts/event_study.py --eval-start {args.eval_start}"
            f" --eval-end {args.eval_end} --horizon-minutes {args.horizon_minutes}`\n"
            f"- git commit: `{commit}`\n"
            f"- scheduled decisions in window: {len(decisions)}\n"
            f"- inference device: {args.device}\n"
            f"- decisions with index and FX data: {m_a}\n"
            f"- consensus surprises: {m_s}\n"
            f"- FX alignment basis: {', '.join(bases) if bases else 'none'}\n"
            f"- horizon after release: {args.horizon_minutes} minutes (intraday) "
            f"or next available daily rate\n"
            f"- result: {summary}\n"
        )
        with open("RESULTS.md", "a", encoding="utf-8") as f:
            f.write(entry)
        print("appended to RESULTS.md")


if __name__ == "__main__":
    main()
