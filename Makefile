PY := .venv/bin/python
CUT := 2025-08-01
EVAL_END := 2026-08-01

.PHONY: test ingest snapshot bootstrap review review-html train ablate eval event-study

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
	$(PY) scripts/train.py --cut-date $(CUT) --export-dir export/cbsent

ablate:
	$(PY) scripts/train.py --cut-date $(CUT) --no-negation-markers \
		--export-dir export/cbsent-no-negation
	$(PY) scripts/ablation.py --cut-date $(CUT) --eval-end $(EVAL_END)

eval:
	$(PY) scripts/eval.py --cut-date $(CUT) --eval-end $(EVAL_END)

event-study:
	$(PY) scripts/event_study.py --eval-start $(CUT) --eval-end $(EVAL_END)
