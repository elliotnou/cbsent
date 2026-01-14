# FinSENT: Monetary Policy Divergence Engine

_"The economy is a dynamic system characterized by evolving human behaviour and
decision-making. Economic relationships change over time, and, to obtain accurate forecast, it is crucial to recognize structural changes as they occur"_ - Cogley & Sargent

Exchange rates like USD/CAD are heavily influenced by monetary policy divergence between central banks. But central bank communications are purely qualitative—dense transcripts, speeches, and minutes that resist mathematical comparison.

I built finSENT as an experimental study to see if LLMs could effectively quantify these dry narratives, allowing us to "see" the sentiment spread in a way that raw text doesn't allow.

[Live Dashboard](https://fin-sent.vercel.app/)


## What It Does

FinSENT is a **Quantitative Narrative Monitor** that automates policy sentiment extraction and visualizes how aligned or divergent the two central banks are at any point in time.

1. **Automated ETL** — Python scrapers monitor official RSS feeds and HTML statements
2. **Sentiment Scoring** — Each communication is analyzed and scored on a hawkish-dovish spectrum
3. **Visualization** — Sentiment spread (Δ) is overlaid against USD/CAD price data to surface correlations between policy language and market movement


## How It Works

### LLM-Based Sentiment Quantification

Rather than keyword matching (which misses context), the system uses GPT-4o-mini to analyze policy statement tone.

- **Scale:** -1.0 (Dovish/Easing) → +1.0 (Hawkish/Tightening)
- **Explainability:** Every score includes a justification grounded in specific transcript phrases

### Asynchronous Alignment

Central banks don't release statements on the same days. To calculate a spread, the engine uses forward-fill (`ffill`) to treat the most recent sentiment as "active" until the next release—enabling daily 1:1 comparison.

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React (Vite), Tailwind CSS, Recharts, GSAP |
| **Backend** | FastAPI, Uvicorn |
| **Data** | Pandas, NumPy, yfinance, PostgreSQL (Neon) |
| **AI** | OpenAI API (GPT-4o-mini) |
| **Infra** | GitHub Actions, Render, Vercel |

## License

MIT
