PY := .venv/bin/python

.PHONY: test ingest snapshot

test:
	$(PY) -m pytest tests/ -q

ingest:
	$(PY) scripts/ingest.py

snapshot:
	$(PY) scripts/export_snapshot.py
