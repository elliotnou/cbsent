# RESULTS

Append-only log of every reported number. Each entry records the command
that produced it, the git commit it ran at, and the date it ran. Numbers
that do not appear here do not exist.

---

## Corpus, Phase 1 (2026-08-11)

- command: `python scripts/ingest.py && python scripts/export_snapshot.py`
- git commit: `c702ec6`

| source | documents | sentences | first release | last release |
|---|---|---|---|---|
| FOMC statements | 40 | | 2021-09-22 | 2026-07-29 |
| FOMC minutes | 39 | | 2021-10-13 | 2026-07-08 |
| BoC rate announcements | 40 | | 2021-09-08 | 2026-07-15 |
| total | 119 | 11868 | | |

Coverage check: the Bank of Canada holds eight fixed announcement dates
per year and the corpus contains exactly eight for each of 2022, 2023,
2024 and 2025. The FOMC holds eight meetings per year and the corpus
contains eight statements for each full year.

Release timestamps: all 79 Fed documents are stamped 14:00 ET. Of the 40
BoC announcements, 19 are stamped 10:00 ET (every announcement through
2023) and 21 are stamped 09:45 ET (every announcement from 2024-01-24),
matching the Bank's December 2023 change to its communication schedule.

Held-out window: 2025-08-01 to 2026-08-01, containing 16 scheduled rate
decisions (8 Fed, 8 BoC). Training window: 2021-08-01 to 2025-08-01.
