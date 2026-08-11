PY := .venv/bin/python
CUT := 2025-08-01
EVAL_END := 2026-08-01
# Best-by-validation checkpoint is kept within the run; see RESULTS.md.
EPOCHS := 14

.PHONY: test ingest snapshot bootstrap export-labels review review-html train \
	ablate ablate-single eval eval-provisional event-study probe cost all

test:
	$(PY) -m pytest tests/ -q

ingest:
	$(PY) scripts/ingest.py

snapshot:
	$(PY) scripts/export_snapshot.py

bootstrap:
	$(PY) scripts/bootstrap_labels.py
	$(PY) scripts/export_llm_labels.py

export-labels:
	$(PY) scripts/export_llm_labels.py

review:
	$(PY) labeling/review.py --eval-start $(CUT)

review-html:
	$(PY) labeling/review_html.py --eval-start $(CUT)

train:
	$(PY) scripts/train.py --cut-date $(CUT) --epochs $(EPOCHS) \
		--export-dir export/cbsent

ablate:
	$(PY) scripts/ablation_sweep.py --allow-bootstrap

ablate-single:
	$(PY) scripts/train.py --cut-date $(CUT) --epochs $(EPOCHS) \
		--no-negation-markers --export-dir export/cbsent-no-negation
	$(PY) scripts/ablation.py --cut-date $(CUT) --eval-end $(EVAL_END)

# Strict by default: refuses to score against bootstrap labels.
eval:
	$(PY) scripts/eval.py --cut-date $(CUT) --eval-end $(EVAL_END)

# Reproduces the provisional table currently recorded in RESULTS.md.
eval-provisional:
	$(PY) scripts/eval.py --cut-date $(CUT) --eval-end $(EVAL_END) --allow-bootstrap

event-study:
	$(PY) scripts/event_study.py --eval-start $(CUT) --eval-end $(EVAL_END)

probe:
	$(PY) scripts/negation_probe.py

cost:
	$(PY) scripts/cost_compare.py --input-price 1.25 --output-price 10.00 \
		--price-source https://developers.openai.com/api/docs/pricing

all: train eval-provisional probe event-study cost
