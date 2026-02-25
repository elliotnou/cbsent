# FinSENT

**Monetary policy sentiment engine.** Quantifies Fed and Bank of Canada hawkish/dovish tone, visualizes the divergence, and overlays it against USD/CAD.

[Live Dashboard](https://fin-sent.vercel.app/)

---

## How It Works

```
Scrape → Split → Score → Aggregate
```

1. **Scrapers** pull new transcripts from `federalreserve.gov` and `bankofcanada.ca` hourly via GitHub Actions
2. Each transcript is split into sentences
3. A fine-tuned **DistilBERT** model scores every sentence on two axes — stance `[-1, +1]` and topic (5 classes)
4. Sentences are weighted by topic relevance and aggregated into a single transcript score

### The Model

Multi-task DistilBERT trained via **distillation from GPT-4o-mini** labels on 3,624 central bank sentences.

| | |
|---|---|
| **Backbone** | `distilbert-base-uncased` (66M params) |
| **Head 1** | Regression → stance score ∈ [-1, +1] via tanh |
| **Head 2** | Classification → topic (Inflation, Growth, Employment, Guidance, Boilerplate) |
| **Loss** | MSE(score) + CrossEntropy(topic) |
| **Results** | MAE = 0.186 · Topic Acc = 77% · Inflation F1 = 92% |

### Topic Weights

| Inflation | Guidance | Employment | Growth | Boilerplate |
|:---------:|:--------:|:----------:|:------:|:-----------:|
| 1.0 | 1.0 | 0.7 | 0.7 | 0.0 |

```
transcript_score = Σ(stance × weight) / Σ(weight)
divergence = Fed_score − BoC_score
```

---

## Features

- **Dashboard** — Score bar, Fed/BoC/USD-CAD snapshot cards, divergence & sentiment charts with stat overlays
- **Transcripts** — Browse every scraped document with expandable sentence-level scoring
- **Policy Analyst** — GPT-4o-mini chatbot with tool-use that queries the sentiment database in natural language
- **Docs** — Full system documentation page explaining the pipeline, model, scoring, and chatbot
- **Dark / Light mode** — System-wide theme toggle

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React, Vite, Tailwind, Recharts |
| Backend | FastAPI, PostgreSQL (Neon) |
| ML | PyTorch, Hugging Face Transformers, DistilBERT |
| Chat | GPT-4o-mini with function calling |
| Infra | GitHub Actions, Render, Vercel |

## Structure

```
backend/
├── analysis/
│   ├── model/              # Multi-task DistilBERT (definition, training, export)
│   ├── sentiment_eng.py    # Inference engine
│   └── batch_processor.py  # Scores unprocessed transcripts
├── scrapers/               # Fed & BoC document scrapers
├── chat.py                 # GPT-4o-mini agent with SQL tools
└── main.py                 # FastAPI server

frontend/src/components/
├── DivergenceChart.tsx     # Dashboard (charts, cards, score bar)
├── TranscriptsPage.tsx     # Sentence-level transcript browser
├── ChatPage.tsx            # Policy Analyst chatbot
└── DocsPage.tsx            # System documentation
```

## Data Sources

- [Federal Reserve](https://www.federalreserve.gov) — Monetary policy press releases
- [Bank of Canada](https://www.bankofcanada.ca) — Interest rate announcements & MPRs

## License

MIT
