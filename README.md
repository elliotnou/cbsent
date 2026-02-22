# FinSENT: Monetary Policy Divergence Engine

_"The economy is a dynamic system characterized by evolving human behaviour and
decision-making. Economic relationships change over time, and, to obtain accurate forecast, it is crucial to recognize structural changes as they occur"_ - Cogley & Sargent

Exchange rates like USD/CAD are heavily influenced by monetary policy divergence between central banks. But central bank communications are purely qualitative—dense transcripts, speeches, and minutes that resist mathematical comparison.

I built finSENT as an experimental study to see if NLP and deep learning could effectively quantify these dry narratives, allowing us to "see" the sentiment spread in a way that raw text doesn't allow.

[Live Dashboard](https://fin-sent.vercel.app/)


## What It Does

FinSENT is a **Quantitative Narrative Monitor** that automates policy sentiment extraction and visualizes how aligned or divergent the two central banks are at any point in time.

1. **Automated ETL** — Python scrapers monitor official RSS feeds and HTML statements
2. **Sentiment Scoring** — Each communication is analyzed sentence-by-sentence using a fine-tuned DistilBERT model and scored on a hawkish-dovish spectrum
3. **Visualization** — Sentiment spread (Δ) is overlaid against USD/CAD price data to surface correlations between policy language and market movement


## How It Works

### Fine-Tuned DistilBERT Sentiment Model

The system uses a custom **multi-task DistilBERT** model fine-tuned specifically for central bank sentiment analysis. Rather than relying on keyword matching or generic API calls, the model was trained via **model distillation** — using GPT-4o-mini–generated labels as ground-truth targets to train a smaller, self-hosted BERT model that runs entirely offline.

**Model Architecture:**
- **Backbone:** `distilbert-base-uncased` (Hugging Face Transformers / PyTorch)
- **Regression Head:** Predicts stance score in [-1.0, +1.0] (dovish → hawkish) via shared [CLS] representation
- **Classification Head:** Classifies topic (Inflation, Growth, Employment, Guidance, Boilerplate) for impact-weight assignment

**Training Pipeline:**
- 3,624 GPT-labeled sentences used as distillation targets (80/20 stratified train/val split)
- Combined loss: MSE (stance regression) + CrossEntropy (topic classification)
- AdamW optimizer with gradient clipping, 10 epochs, best-model checkpointing
- **Results:** MAE = 0.186, Topic Accuracy = 77% (Inflation F1: 92%, Growth F1: 85%)

### Asynchronous Alignment

Central banks don't release statements on the same days. To calculate a spread, the engine uses forward-fill (`ffill`) to treat the most recent sentiment as "active" until the next release—enabling daily 1:1 comparison.

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React (Vite), Tailwind CSS, Recharts, GSAP |
| **Backend** | FastAPI, Uvicorn |
| **Data** | Pandas, NumPy, yfinance, PostgreSQL (Neon) |
| **ML / NLP** | PyTorch, Hugging Face Transformers, DistilBERT, scikit-learn |
| **Infra** | GitHub Actions, Render, Vercel |

## Project Structure

```
backend/
├── analysis/
│   ├── model/
│   │   ├── distilbert_model.py    # Multi-task PyTorch model definition
│   │   ├── train_distilbert.py    # Training pipeline (model distillation)
│   │   └── export/                # Saved model weights, tokenizer, metadata
│   ├── sentiment_eng.py           # DistilBERT inference engine
│   └── batch_processor.py         # Scores unprocessed transcripts
├── scrapers/                      # Fed & BoC document scrapers
├── main.py                        # FastAPI server
└── requirements.txt
frontend/
├── src/components/
│   ├── DivergenceChart.tsx        # Main sentiment spread visualization
│   └── TranscriptsPage.tsx        # Sentence-level breakdown view
└── ...
```

## Data Sources & Attribution

### Primary Sources
- **Federal Reserve Monetary Policy Press Releases**: [Board of Governors of the Federal Reserve System](https://www.federalreserve.gov)
- **Bank of Canada Press Releases**: [Bank of Canada](https://www.bankofcanada.ca)

## License

MIT
