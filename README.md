#  FinSight — Autonomous Financial Research Agent

> Multi-agent AI system that generates institutional-grade investment research briefs for any publicly traded stock in ~60 seconds.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Claude API](https://img.shields.io/badge/Claude-Sonnet%204.5-orange)](https://anthropic.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

##  What It Does

Enter any stock ticker → 4 specialized AI agents run in parallel → Get a professional BUY/HOLD/SELL research brief with full reasoning in ~20 seconds.

##  Architecture
```
User Input (ticker)
        ↓
  Orchestrator Agent (Claude Sonnet 4.5)
  ↙       ↓        ↘        ↘
Agent 1  Agent 2  Agent 3  Agent 4
Finance  Sentiment Technical  SEC RAG
yfinance  Claude   TA-Lib   ChromaDB
        ↓
  Synthesis Agent (Claude Sonnet 4.5)
        ↓
  BUY/HOLD/SELL + Confidence Score + Full Thesis
```

## Agent Breakdown

| Agent | Data Source | Signals Generated |
|-------|------------|-------------------|
|  Financial Agent | yfinance | P/E, revenue growth, margins, FCF, ROE |
|  Sentiment Agent | yfinance news + Claude | News tone, catalysts, risks |
|  Technical Agent | Price history + TA-Lib | RSI, MACD, Bollinger Bands, MAs |
|  RAG Agent | SEC EDGAR 10-K/10-Q + ChromaDB | Risk factors, guidance, competition |
|  Synthesis Agent | All agent outputs + Claude | Final BUY/HOLD/SELL + investment thesis |

## Tech Stack

- **LLM:** Claude Sonnet 4.5 (Anthropic API)
- **RAG:** ChromaDB vector database + sentence-transformers (all-MiniLM-L6-v2)
- **Financial Data:** SEC EDGAR API (free), yfinance
- **Technical Analysis:** TA-Lib (RSI, MACD, Bollinger Bands, Moving Averages)
- **Web UI:** Streamlit
- **Language:** Python 3.11

## Key Technical Achievements

- **RAG pipeline** over 200-page SEC 10-K/10-Q filings (245+ ChromaDB chunks per stock)
- **Multi-agent orchestration** built from first principles — no LangChain
- **4 specialized agents** with independent signal generation and confidence scoring
- **30 second** end-to-end analysis time
- **Full reasoning transparency** — every signal traceable to source data

## Project Structure
```
finsight/
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py          # Master coordinator
│   ├── financial_agent.py       # Fundamentals analysis
│   ├── sentiment_agent.py       # News sentiment
│   ├── technical_agent.py       # Technical indicators
│   └── rag_agent.py             # SEC filing RAG
├── tools/
│   ├── __init__.py
│   ├── data_fetcher.py          # yfinance wrapper
│   ├── technical_indicators.py  # TA-Lib calculations
│   ├── sec_fetcher.py           # SEC EDGAR API
│   └── vector_store.py          # ChromaDB RAG pipeline
├── backend/
│   ├── main.py                  # FastAPI server
│   ├── requirements.txt         # Backend dependencies
│   └── Dockerfile               # Backend container
├── frontend/
│   ├── public/index.html
│   ├── src/
│   │   ├── App.jsx              # Main React component
│   │   ├── index.js
│   │   └── index.css
│   ├── package.json
│   └── Dockerfile               # Frontend container
├── output/
│   ├── reports/                 # Generated JSON reports
│   └── chromadb/                # Vector store
├── docker-compose.yml           # Run everything
├── app.py                       # Streamlit UI
├── main.py                      # CLI entry point
├── config.py                    # Settings
├── requirements.txt
├── .env                         # API keys (never committed)
├── .gitignore
├── LICENSE
└── README.md
```

## Disclaimer

This tool is for research and educational purposes only. Not financial advice. Always consult a qualified financial advisor before making investment decisions.

##  License

MIT License — see [LICENSE](LICENSE)
