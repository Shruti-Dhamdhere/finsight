from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import run_orchestrator
from backend.auth import get_current_user, check_usage_limit, increment_usage, log_analysis
from backend.payments import create_checkout_session, create_portal_session, handle_webhook

app = FastAPI(title="FinSight API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=4)


class AnalyzeRequest(BaseModel):
    ticker: str


STOCKS = [
    {"ticker": "AAPL", "name": "Apple Inc."},
    {"ticker": "NVDA", "name": "NVIDIA Corporation"},
    {"ticker": "MSFT", "name": "Microsoft Corporation"},
    {"ticker": "GOOGL", "name": "Alphabet Inc."},
    {"ticker": "AMZN", "name": "Amazon.com Inc."},
    {"ticker": "META", "name": "Meta Platforms Inc."},
    {"ticker": "TSLA", "name": "Tesla Inc."},
    {"ticker": "BRKB", "name": "Berkshire Hathaway"},
    {"ticker": "JPM", "name": "JPMorgan Chase"},
    {"ticker": "V", "name": "Visa Inc."},
    {"ticker": "JNJ", "name": "Johnson & Johnson"},
    {"ticker": "WMT", "name": "Walmart Inc."},
    {"ticker": "XOM", "name": "Exxon Mobil"},
    {"ticker": "UNH", "name": "UnitedHealth Group"},
    {"ticker": "MA", "name": "Mastercard Inc."},
    {"ticker": "PG", "name": "Procter & Gamble"},
    {"ticker": "HD", "name": "Home Depot"},
    {"ticker": "CVX", "name": "Chevron Corporation"},
    {"ticker": "MRK", "name": "Merck & Co."},
    {"ticker": "LLY", "name": "Eli Lilly"},
    {"ticker": "ABBV", "name": "AbbVie Inc."},
    {"ticker": "PEP", "name": "PepsiCo Inc."},
    {"ticker": "KO", "name": "Coca-Cola Company"},
    {"ticker": "AVGO", "name": "Broadcom Inc."},
    {"ticker": "COST", "name": "Costco Wholesale"},
    {"ticker": "TMO", "name": "Thermo Fisher Scientific"},
    {"ticker": "CSCO", "name": "Cisco Systems"},
    {"ticker": "ACN", "name": "Accenture"},
    {"ticker": "ABT", "name": "Abbott Laboratories"},
    {"ticker": "MCD", "name": "McDonald's Corporation"},
    {"ticker": "DHR", "name": "Danaher Corporation"},
    {"ticker": "NEE", "name": "NextEra Energy"},
    {"ticker": "TXN", "name": "Texas Instruments"},
    {"ticker": "QCOM", "name": "Qualcomm Inc."},
    {"ticker": "AMD", "name": "Advanced Micro Devices"},
    {"ticker": "INTU", "name": "Intuit Inc."},
    {"ticker": "AMGN", "name": "Amgen Inc."},
    {"ticker": "RTX", "name": "Raytheon Technologies"},
    {"ticker": "HON", "name": "Honeywell International"},
    {"ticker": "IBM", "name": "International Business Machines"},
    {"ticker": "GS", "name": "Goldman Sachs"},
    {"ticker": "MS", "name": "Morgan Stanley"},
    {"ticker": "BAC", "name": "Bank of America"},
    {"ticker": "WFC", "name": "Wells Fargo"},
    {"ticker": "C", "name": "Citigroup Inc."},
    {"ticker": "BLK", "name": "BlackRock Inc."},
    {"ticker": "SPGI", "name": "S&P Global"},
    {"ticker": "AXP", "name": "American Express"},
    {"ticker": "SCHW", "name": "Charles Schwab"},
    {"ticker": "USB", "name": "U.S. Bancorp"},
    {"ticker": "NFLX", "name": "Netflix Inc."},
    {"ticker": "DIS", "name": "Walt Disney Company"},
    {"ticker": "CMCSA", "name": "Comcast Corporation"},
    {"ticker": "T", "name": "AT&T Inc."},
    {"ticker": "VZ", "name": "Verizon Communications"},
    {"ticker": "TMUS", "name": "T-Mobile US"},
    {"ticker": "UBER", "name": "Uber Technologies"},
    {"ticker": "LYFT", "name": "Lyft Inc."},
    {"ticker": "ABNB", "name": "Airbnb Inc."},
    {"ticker": "SNAP", "name": "Snap Inc."},
    {"ticker": "SPOT", "name": "Spotify Technology"},
    {"ticker": "SQ", "name": "Block Inc."},
    {"ticker": "PYPL", "name": "PayPal Holdings"},
    {"ticker": "SHOP", "name": "Shopify Inc."},
    {"ticker": "CRM", "name": "Salesforce Inc."},
    {"ticker": "ORCL", "name": "Oracle Corporation"},
    {"ticker": "SAP", "name": "SAP SE"},
    {"ticker": "NOW", "name": "ServiceNow Inc."},
    {"ticker": "SNOW", "name": "Snowflake Inc."},
    {"ticker": "PLTR", "name": "Palantir Technologies"},
    {"ticker": "NET", "name": "Cloudflare Inc."},
    {"ticker": "ZS", "name": "Zscaler Inc."},
    {"ticker": "CRWD", "name": "CrowdStrike Holdings"},
    {"ticker": "DDOG", "name": "Datadog Inc."},
    {"ticker": "MDB", "name": "MongoDB Inc."},
    {"ticker": "COIN", "name": "Coinbase Global"},
    {"ticker": "HOOD", "name": "Robinhood Markets"},
    {"ticker": "BA", "name": "Boeing Company"},
    {"ticker": "CAT", "name": "Caterpillar Inc."},
    {"ticker": "GE", "name": "GE Aerospace"},
    {"ticker": "MMM", "name": "3M Company"},
    {"ticker": "DE", "name": "Deere & Company"},
    {"ticker": "LMT", "name": "Lockheed Martin"},
    {"ticker": "NOC", "name": "Northrop Grumman"},
    {"ticker": "F", "name": "Ford Motor Company"},
    {"ticker": "GM", "name": "General Motors"},
    {"ticker": "RIVN", "name": "Rivian Automotive"},
    {"ticker": "LCID", "name": "Lucid Group"},
    {"ticker": "NIO", "name": "NIO Inc."},
    {"ticker": "PFE", "name": "Pfizer Inc."},
    {"ticker": "MRNA", "name": "Moderna Inc."},
    {"ticker": "BNTX", "name": "BioNTech SE"},
    {"ticker": "GILD", "name": "Gilead Sciences"},
    {"ticker": "BIIB", "name": "Biogen Inc."},
    {"ticker": "REGN", "name": "Regeneron Pharmaceuticals"},
    {"ticker": "VRTX", "name": "Vertex Pharmaceuticals"},
    {"ticker": "SPY", "name": "SPDR S&P 500 ETF"},
    {"ticker": "QQQ", "name": "Invesco QQQ Trust"},
    {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF"},
]


@app.get("/")
def root():
    return {"status": "FinSight API running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/search")
async def search_stocks(q: str = ""):
    """Search any publicly listed stock globally using yfinance live search
    with fuzzy fallback on local list if yfinance is unavailable."""
    if not q or len(q) < 1:
        return []

    # 1. Try live yfinance search first
    try:
        import yfinance as yf
        search = yf.Search(q, max_results=10, enable_fuzzy_query=True)
        quotes = search.quotes or []
        results = []
        for item in quotes:
            ticker = item.get("symbol", "")
            name = item.get("longname") or item.get("shortname") or ""
            exchange = item.get("exchange", "")
            quote_type = item.get("quoteType", "")
            if quote_type in ["EQUITY", "ETF"] and ticker and name:
                results.append({"ticker": ticker, "name": name, "exchange": exchange, "type": quote_type})
        if results:
            return results[:8]
    except Exception:
        pass

    # 2. Fuzzy fallback on local STOCKS list
    from difflib import SequenceMatcher
    def fuzzy_score(item, query):
        q_low = query.lower()
        ticker_score = SequenceMatcher(None, q_low, item["ticker"].lower()).ratio()
        name_score = SequenceMatcher(None, q_low, item["name"].lower()).ratio()
        ticker_prefix = 1.0 if item["ticker"].lower().startswith(q_low) else 0.0
        name_prefix = 0.8 if item["name"].lower().startswith(q_low) else 0.0
        return max(ticker_score, name_score, ticker_prefix, name_prefix)
    scored = [(s, fuzzy_score(s, q)) for s in STOCKS]
    scored = [(s, score) for s, score in scored if score > 0.3]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in scored[:8]]


@app.get("/chart/{ticker}")
async def get_chart_data(ticker: str, period: str = "1M"):
    """Get historical price data for charting — no auth required."""
    try:
        import yfinance as yf

        period_map = {
            "1D": "1d", "1W": "5d", "1M": "1mo", "3M": "3mo",
            "6M": "6mo", "1Y": "1y", "5Y": "5y", "MAX": "max"
        }
        interval_map = {
            "1D": "5m", "1W": "1h", "1M": "1d", "3M": "1d",
            "6M": "1d", "1Y": "1d", "5Y": "1wk", "MAX": "1mo"
        }

        yf_period = period_map.get(period, "1mo")
        yf_interval = interval_map.get(period, "1d")

        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=yf_period, interval=yf_interval)

        if hist.empty:
            raise HTTPException(status_code=404, detail="No data found")

        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": str(date),
                "close": round(float(row["Close"]), 2),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "volume": int(row["Volume"])
            })

        first_price = data[0]["close"] if data else 0
        last_price = data[-1]["close"] if data else 0
        change_pct = round(((last_price - first_price) / first_price) * 100, 2) if first_price else 0

        return {
            "ticker": ticker.upper(),
            "period": period,
            "data": data,
            "change_pct": change_pct,
            "is_positive": change_pct >= 0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze_stock(
    request: AnalyzeRequest,
    current_user=Depends(get_current_user)
):
    ticker = request.ticker.upper().strip()

    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    profile = check_usage_limit(current_user.id)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, run_orchestrator, ticker)

        if result.get("status") != "success":
            raise HTTPException(status_code=500, detail="Analysis failed")

        increment_usage(current_user.id)
        log_analysis(
            user_id=current_user.id,
            ticker=ticker,
            recommendation=result["recommendation"]["recommendation"],
            confidence=result["recommendation"]["confidence_score"],
            elapsed=result["elapsed_seconds"]
        )

        if "agent_results" in result:
            fin = result["agent_results"].get("financial", {})
            if "raw_data" in fin:
                fin["raw_data"].pop("price_history", None)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/me")
def get_me(current_user=Depends(get_current_user)):
    from backend.auth import get_user_profile
    profile = get_user_profile(current_user.id)
    return {
        "id": current_user.id,
        "email": current_user.email,
        "tier": profile.get("tier", "free"),
        "analyses_today": profile.get("analyses_today", 0),
        "daily_limit": int(os.getenv("FREE_TIER_DAILY_LIMIT", 3))
        if profile.get("tier") == "free" else None
    }


@app.get("/history")
def get_history(current_user=Depends(get_current_user)):
    from backend.auth import supabase
    result = supabase.table("usage_logs").select("*").eq(
        "user_id", current_user.id
    ).order("created_at", desc=True).limit(50).execute()
    return result.data


@app.post("/create-checkout")
def create_checkout(current_user=Depends(get_current_user)):
    url = create_checkout_session(current_user.id, current_user.email)
    return {"checkout_url": url}


@app.post("/create-portal")
def create_portal(current_user=Depends(get_current_user)):
    url = create_portal_session(current_user.id)
    return {"portal_url": url}


@app.post("/webhook")
async def stripe_webhook(request: Request):
    return await handle_webhook(request)


@app.get("/reports/{ticker}")
async def get_report(ticker: str, current_user=Depends(get_current_user)):
    import json
    ticker = ticker.upper()
    report_path = f"./output/reports/{ticker}_report.json"
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail=f"No report found for {ticker}")
    with open(report_path) as f:
        return json.load(f)