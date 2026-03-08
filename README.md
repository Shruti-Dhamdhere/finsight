# Sovvy — AI-Powered Investment Research for Everyone

> Multi-agent financial research system that generates personalised investment analysis in plain English — built for people who want to invest but don't know where to start.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Claude API](https://img.shields.io/badge/Claude-Sonnet-orange)](https://anthropic.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue)](https://reactjs.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## What Sovvy Does

Most investment tools are built for traders. Sovvy is built for everyone else.

Enter any stock ticker, or ask a question like **"what are the top 5 stocks for someone saving $400/month?"** — and four AI agents run in parallel to produce a complete investment brief in plain English, personalised to your financial situation.

A teacher and a software engineer analysing the same stock get different output. Not because of a different template — because the underlying signals are synthesised through the lens of their goals, budget, risk tolerance, and financial literacy level.

```
User Question (ticker or natural language)
           ↓
    Orchestrator (Claude Sonnet)
    ↙        ↓        ↘        ↘
 Financial  Sentiment  Technical  SEC RAG
 Agent      Agent      Agent      Agent
 yfinance   Claude     TA-Lib    ChromaDB
    ↘        ↓        ↙        ↙
     Synthesis Agent (Claude Sonnet)
     + User Profile Context Injection
           ↓
   Plain English Brief + Full Institutional Report
```

**Fresh analysis: ~20 seconds. Repeat analysis: instant (cached).**

---

## Key Features

**For users learning to invest**
- Plain English explanations — jargon defined in context, not assumed
- "What should I invest in given my situation?" natural language queries
- Personalised to your experience level, goals, monthly budget, and risk tolerance
- Investment Thesis written at your reading level
- Beginner summary: what this actually means for you, in two sentences

**For experienced investors**
- Full institutional-grade brief: thesis, bull/bear cases, catalysts, risks, position sizing
- Technical indicators: RSI, MACD, Bollinger Bands, volume analysis
- SEC 10-K/10-Q RAG pipeline: 200+ chunks per stock, ChromaDB vector search
- Downloadable PDF report
- Watchlist with daily morning brief

**Architecture**
- 4 specialist agents run in parallel (financial + sentiment + RAG simultaneously)
- Sequential only where dependencies require it (technical uses price history from financial)
- In-memory cache with 6h TTL — same ticker returns in <100ms
- ChromaDB persists across sessions — SEC filings rebuilt only when stale (7-day TTL)
- Streaming SSE endpoint — user sees first token in ~1s

---

## Agent Breakdown

| Agent | Data Source | What It Analyses |
|-------|------------|-----------------|
| Financial Agent | yfinance | P/E ratio, revenue growth, profit margins, FCF, ROE, 52-week range |
| Sentiment Agent | yfinance news + Claude | News tone, analyst rating changes, market catalysts |
| Technical Agent | Price history + TA-Lib | RSI, MACD, Bollinger Bands, moving averages, volume profile |
| RAG Agent | SEC EDGAR 10-K/10-Q + ChromaDB | Risk factors, management guidance, competition, growth drivers |
| Synthesis Agent | All agent outputs + user profile | Final recommendation calibrated to investor context |

---

## Technical Architecture

```
backend/
├── main.py              # FastAPI — /analyze, /profile, /watchlist, /stream
├── auth.py              # Supabase JWT verification + usage limits
└── payments.py          # Stripe checkout + webhook

agents/
├── orchestrator.py      # Async parallel execution + cache + user profile injection
├── financial_agent.py   # Fundamentals via yfinance
├── sentiment_agent.py   # News sentiment via Claude
├── technical_agent.py   # Technical indicators via TA-Lib
└── rag_agent.py         # SEC filing RAG via ChromaDB

tools/
├── data_fetcher.py      # yfinance wrapper
├── technical_indicators.py  # TA-Lib calculations
├── sec_fetcher.py       # SEC EDGAR API (free, no key)
└── vector_store.py      # ChromaDB with 7-day persistence TTL

frontend/src/
├── App.js               # Main React app — dark UI, SVG charts, tooltips
├── Auth.js              # Supabase login + Google OAuth
└── Onboarding.js        # 4-question investor profile flow
```

**Stack:** Python 3.11, FastAPI, Claude API (Anthropic), ChromaDB, sentence-transformers, TA-Lib, yfinance, SEC EDGAR API, React, Supabase, Stripe, APScheduler

---

## Personalisation System

After a 4-question onboarding (30 seconds), every analysis adapts to the user:

```
Experience:          beginner | intermediate | experienced
Goal:                grow_savings | income | learn
Monthly budget:      <$200 | $200-500 | $500+
Risk tolerance:      low | medium | high
```

These are injected into the synthesis prompt at runtime. A beginner with low risk tolerance receives:
- Plain English throughout, jargon defined inline
- Capital preservation framed prominently
- Position sizing in dollar amounts matching their budget
- 2-sentence plain English summary of what to actually do

An experienced investor receives:
- Standard financial terminology
- Precise quantitative framing
- Institutional-style position sizing rationale

The same 4 agents run. The same signals are collected. The synthesis layer is what changes.

---

## Performance

| Metric | Value |
|--------|-------|
| Fresh analysis (cold) | ~20s |
| Repeat analysis (cache hit) | <100ms |
| Phase 1 — parallel agents | ~13-15s |
| Phase 2 — technical agent | ~2-3s |
| Synthesis — Claude | ~3-5s |
| SEC vector store (first build) | ~15s |
| SEC vector store (from disk) | <500ms |

Latency breakdown verified on Apple Silicon M4, TSLA analysis, March 2025.

---

## Key Technical Contributions

- **User-context-aware synthesis** — persistent investor profile injected into multi-agent synthesis layer; same signals produce qualitatively different output for different investor archetypes
- **Parallel async orchestration built from first principles** — no LangChain; asyncio.gather() across specialist agents with run_in_executor for blocking I/O
- **Persistent RAG with TTL** — ChromaDB collections persist across sessions with freshness checks; 7-day TTL before rebuild; eliminates 15s embedding cost on repeat requests
- **Two-layer output** — plain English brief for retail investors + full institutional report (PDF) for traders; same underlying analysis, different presentation layer
- **Natural language financial queries** — "top 5 stocks for a teacher saving $300/month" resolved through profile-aware synthesis, not retrieval

---

## Setup

### Prerequisites
- Python 3.11 (Apple Silicon: use arm64 conda)
- Node.js 18+
- TA-Lib C library: `brew install ta-lib`
- Supabase project
- Anthropic API key
- Stripe account (optional, for payments)

### Backend

```bash
git clone https://github.com/Shruti-Dhamdhere/finsight
cd finsight
conda activate finrl_trading

pip install fastapi uvicorn anthropic supabase stripe yfinance \
            chromadb sentence-transformers ta-lib apscheduler \
            python-dotenv pandas numpy

cp .env.example .env  # add your API keys
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### Environment Variables

```env
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID=
FREE_TIER_DAILY_LIMIT=20
```

### Database

Run `migrations/v2_schema.sql` in Supabase SQL Editor. Creates:
- `user_profiles` — investor onboarding data
- `watchlist` — per-user ticker tracking
- `signal_log` — every recommendation for backtesting

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze` | Full analysis — returns JSON |
| POST | `/analyze/stream` | SSE streaming — tokens as Claude generates |
| GET/POST | `/profile` | Investor onboarding profile |
| GET/POST/DELETE | `/watchlist` | Watchlist management |
| GET | `/watchlist/brief` | Morning brief for all watchlist tickers |
| GET | `/search?q=` | Live stock search via yfinance |
| GET | `/chart/{ticker}` | OHLCV price history |
| GET | `/me` | Current user profile + usage |

---

## Related Work

This system builds on and extends prior work in multi-agent financial AI:

- **FinRobot** (AI4Finance, 2024) — multi-agent financial analysis, institutional focus, no user personalisation
- **TradingAgents** (Xiao et al., 2024) — LLM trading framework, optimises returns, no literacy adaptation
- **FinArena** (2025) — human-agent collaboration with risk preferences, stock prediction focus
- **AlphaAgents** (2025) — risk-profile embedding in agents, binary risk levels, institutional target
- **FinPersona/SIGIR 2025** — conversational personalised advisor, single agent, no multi-specialist synthesis
- **FinSight** (Jin et al., 2025) — institutional report generation, professional analysts, no retail adaptation

Sovvy is the first system to combine multi-specialist parallel synthesis with multi-dimensional retail investor context (literacy level + goal + budget + risk tolerance) to produce comprehension-calibrated investment output.

---

## Disclaimer

For research and educational purposes only. Not financial advice. Always consult a qualified financial advisor before making investment decisions.

---

## License

MIT — see [LICENSE](LICENSE)
