"""Render the review queue as a single self-contained HTML page.

Some reviewers would rather click than type. This writes one HTML file
with the whole queue, records decisions in the browser, and exports a CSV
that scripts/import_review.py loads back into the labels table. The CLI
reviewer in review.py writes to the database directly and needs no
import step; both produce identical label rows.

Usage:
    python labeling/review_html.py [--eval-start 2025-08-01] [--limit 400]
    python scripts/import_review.py reviewed.csv
"""

import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cbsent.ingest import db
from cbsent.labels import TOPICS
from labeling.review import build_queue

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>cbsent label review</title>
<style>
  body {{ font: 15px/1.55 -apple-system, BlinkMacSystemFont, sans-serif;
          margin: 0 auto; max-width: 820px; padding: 24px; color: #1a1a1a; }}
  header {{ position: sticky; top: 0; background: #fff; padding: 12px 0;
            border-bottom: 1px solid #ddd; }}
  .card {{ border: 1px solid #e0e0e0; border-radius: 6px; padding: 14px;
           margin: 14px 0; }}
  .card.done {{ opacity: 0.5; }}
  .meta {{ font-size: 12px; color: #666; margin-bottom: 8px;
           text-transform: uppercase; letter-spacing: 0.04em; }}
  .tag {{ display: inline-block; padding: 1px 6px; border-radius: 3px;
          background: #eee; margin-right: 6px; }}
  .tag.eval {{ background: #ffe9c7; }}
  .tag.disagree {{ background: #ffd6d6; }}
  .sentence {{ margin-bottom: 10px; }}
  button {{ font: inherit; padding: 5px 11px; margin-right: 5px;
            border: 1px solid #bbb; border-radius: 4px; background: #fafafa;
            cursor: pointer; }}
  button.sel {{ background: #1f4e79; color: #fff; border-color: #1f4e79; }}
  select {{ font: inherit; padding: 4px; }}
  #export {{ background: #1f4e79; color: #fff; border-color: #1f4e79; }}
</style>
<header>
  <strong>cbsent label review</strong>
  <span id="progress"></span>
  <button id="export">Download decisions CSV</button>
</header>
<div id="queue"></div>
<script>
const QUEUE = {queue_json};
const TOPICS = {topics_json};
const decisions = JSON.parse(localStorage.getItem("cbsent_review") || "{{}}");

function save() {{
  localStorage.setItem("cbsent_review", JSON.stringify(decisions));
  const n = Object.keys(decisions).length;
  document.getElementById("progress").textContent =
    "  " + n + " of " + QUEUE.length + " reviewed";
}}

function render() {{
  const root = document.getElementById("queue");
  root.innerHTML = "";
  for (const item of QUEUE) {{
    const card = document.createElement("div");
    card.className = "card" + (decisions[item.id] ? " done" : "");

    const meta = document.createElement("div");
    meta.className = "meta";
    const tagClass = item.in_eval ? "eval" : (item.disagree ? "disagree" : "");
    meta.innerHTML =
      '<span class="tag ' + tagClass + '">' +
      (item.in_eval ? "held-out window" : (item.disagree ? "disagreement" : "sample")) +
      '</span><span class="tag">' + item.bank + " " + item.year + '</span>' +
      "dictionary: " + item.dict_stance + "  |  llm: " + item.llm_stance +
      " / " + item.llm_topic;
    card.appendChild(meta);

    const sentence = document.createElement("div");
    sentence.className = "sentence";
    sentence.textContent = item.text;
    card.appendChild(sentence);

    const controls = document.createElement("div");
    for (const stance of ["hawkish", "dovish", "neutral"]) {{
      const b = document.createElement("button");
      b.textContent = stance;
      if (decisions[item.id] && decisions[item.id].stance === stance) b.className = "sel";
      b.onclick = () => {{
        const topic = card.querySelector("select").value;
        decisions[item.id] = {{ stance: stance, topic: topic }};
        save(); render();
      }};
      controls.appendChild(b);
    }}
    const sel = document.createElement("select");
    for (const t of TOPICS) {{
      const o = document.createElement("option");
      o.value = t; o.textContent = t;
      if ((decisions[item.id] ? decisions[item.id].topic : item.llm_topic) === t) {{
        o.selected = true;
      }}
      sel.appendChild(o);
    }}
    sel.onchange = () => {{
      if (decisions[item.id]) {{
        decisions[item.id].topic = sel.value; save();
      }}
    }};
    controls.appendChild(sel);
    card.appendChild(controls);
    root.appendChild(card);
  }}
  save();
}}

document.getElementById("export").onclick = () => {{
  let csv = "sentence_id,stance,topic\\n";
  for (const [id, d] of Object.entries(decisions)) {{
    csv += id + "," + d.stance + "," + d.topic + "\\n";
  }}
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], {{ type: "text/csv" }}));
  a.download = "reviewed.csv";
  a.click();
}};

render();
</script>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-start", default="2025-08-01")
    parser.add_argument("--sample-per-cell", type=int, default=15)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", default="labeling/review.html")
    args = parser.parse_args()

    with db.connect() as conn:
        queue, n_eval, n_dis, n_neg, n_sample = build_queue(
            conn, args.eval_start, args.sample_per_cell
        )
    if args.limit:
        queue = queue[: args.limit]

    items = [
        {
            "id": sid, "text": text, "bank": bank, "year": year,
            "in_eval": bool(in_eval), "disagree": dict_stance != llm_stance,
            "dict_stance": dict_stance or "", "llm_stance": llm_stance or "",
            "llm_topic": llm_topic or "guidance",
        }
        for sid, text, bank, year, in_eval, dict_stance, llm_stance, llm_topic, _ in queue
    ]

    page = PAGE.format(queue_json=json.dumps(items),
                       topics_json=json.dumps(list(TOPICS)))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {len(items)} sentences to {args.out} "
          f"({n_eval} held-out window, {n_dis} disagreements, "
          f"{n_neg} negation cues, {n_sample} sampled)")
    print("open it, review, download the CSV, then run "
          "python scripts/import_review.py reviewed.csv")


if __name__ == "__main__":
    main()
