PY := .venv/bin/python
CUT := 2025-08-01
EVAL_END := 2026-08-01
# Validation macro-F1 peaks here and declines after; see RESULTS.md.
EPOCHS := 6

.PHONY: test ingest snapshot bootstrap review review-html train ablate eval \
	event-study cost all

test:
	$(PY) -m pytest tests/ -q

ingest:
	$(PY) scripts/ingest.py

snapshot:
	$(PY) scripts/export_snapshot.py

bootstrap:
	$(PY) scripts/bootstrap_labels.py

review:
	$(PY) labeling/review.py --eval-start $(CUT)

review-html:
	$(PY) labeling/review_html.py --eval-start $(CUT)

train:
	$(PY) scripts/train.py --cut-date $(CUT) --epochs $(EPOCHS) \
		--export-dir export/cbsent

ablate:
	$(PY) scripts/train.py --cut-date $(CUT) --epochs $(EPOCHS) \
		--no-negation-markers --export-dir export/cbsent-no-negation
	$(PY) scripts/ablation.py --cut-date $(CUT) --eval-end $(EVAL_END)

eval:
	$(PY) scripts/eval.py --cut-date $(CUT) --eval-end $(EVAL_END)

event-study:
	$(PY) scripts/event_study.py --eval-start $(CUT) --eval-end $(EVAL_END)

cost:
	$(PY) scripts/cost_compare.py --input-price 1.25 --output-price 10.00 \
		--price-source https://developers.openai.com/api/docs/pricing

all: train eval event-study cost
