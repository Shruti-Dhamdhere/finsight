"""
backend/main.py — FinSight v2
==============================
Changes from v1:
- /analyze now calls run_orchestrator_async directly (no run_in_executor wrapper)
- /analyze/stream  NEW — SSE streaming, ~1s to first token
- /profile         NEW — GET/POST investor onboarding profile
- /watchlist       NEW — GET/POST/DELETE + /watchlist/brief morning brief
- /me now returns onboarding_complete flag

All existing endpoints (search, chart, history, checkout, portal, webhook,
reports) are preserved character-for-character from v1.
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import sys, os, asyncio, json
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import (
    run_orchestrator_async,
    stream_analysis,
    UserProfile,
)
from backend.auth import (
    get_current_user,
    check_usage_limit,
    increment_usage,
    log_analysis,
    supabase,
)
from backend.payments import create_checkout_session, create_portal_session, handle_webhook


# ── Background scheduler ───────────────────────────────────────────────────────

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    _scheduler_available = True
except ImportError:
    _scheduler_available = False
    print("[Scheduler] apscheduler not installed — run: pip install apscheduler")


async def _watchlist_refresh():
    """Pre-compute analysis for every watchlisted ticker at 07:30 UTC daily."""
    print("[Scheduler] Starting watchlist pre-compute...")
    try:
        resp    = supabase.table("watchlist").select("ticker").execute()
        tickers = list({row["ticker"] for row in (resp.data or [])})
        print(f"[Scheduler] {len(tickers)} tickers: {tickers}")
        for ticker in tickers:
            try:
                await run_orchestrator_async(ticker)
                print(f"[Scheduler] ✓ {ticker}")
                await asyncio.sleep(2)      # be polite to external APIs
            except Exception as e:
                print(f"[Scheduler] ✗ {ticker}: {e}")
    except Exception as e:
        print(f"[Scheduler] Job failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if _scheduler_available:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            _watchlist_refresh,
            CronTrigger(hour=7, minute=30),
            id="watchlist_refresh",
            replace_existing=True,
        )
        scheduler.start()
        print("[Scheduler] Started — watchlist refresh at 07:30 UTC daily")
        yield
        scheduler.shutdown()
    else:
        yield


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="FinSight API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=4)


# ── Models ─────────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    ticker: str

class ProfileRequest(BaseModel):
    experience:         str = "beginner"
    goal:               str = "grow_savings"
    monthly_investable: str = "200_500"
    risk_tolerance:     str = "medium"

class WatchlistRequest(BaseModel):
    ticker: str


# ── Stock list (unchanged from v1) ────────────────────────────────────────────

STOCKS = [
    {"ticker": "AAPL",  "name": "Apple Inc."},
    {"ticker": "NVDA",  "name": "NVIDIA Corporation"},
    {"ticker": "MSFT",  "name": "Microsoft Corporation"},
    {"ticker": "GOOGL", "name": "Alphabet Inc."},
    {"ticker": "AMZN",  "name": "Amazon.com Inc."},
    {"ticker": "META",  "name": "Meta Platforms Inc."},
    {"ticker": "TSLA",  "name": "Tesla Inc."},
    {"ticker": "BRKB",  "name": "Berkshire Hathaway"},
    {"ticker": "JPM",   "name": "JPMorgan Chase"},
    {"ticker": "V",     "name": "Visa Inc."},
    {"ticker": "JNJ",   "name": "Johnson & Johnson"},
    {"ticker": "WMT",   "name": "Walmart Inc."},
    {"ticker": "XOM",   "name": "Exxon Mobil"},
    {"ticker": "UNH",   "name": "UnitedHealth Group"},
    {"ticker": "MA",    "name": "Mastercard Inc."},
    {"ticker": "PG",    "name": "Procter & Gamble"},
    {"ticker": "HD",    "name": "Home Depot"},
    {"ticker": "CVX",   "name": "Chevron Corporation"},
    {"ticker": "MRK",   "name": "Merck & Co."},
    {"ticker": "LLY",   "name": "Eli Lilly"},
    {"ticker": "ABBV",  "name": "AbbVie Inc."},
    {"ticker": "PEP",   "name": "PepsiCo Inc."},
    {"ticker": "KO",    "name": "Coca-Cola Company"},
    {"ticker": "AVGO",  "name": "Broadcom Inc."},
    {"ticker": "COST",  "name": "Costco Wholesale"},
    {"ticker": "TMO",   "name": "Thermo Fisher Scientific"},
    {"ticker": "CSCO",  "name": "Cisco Systems"},
    {"ticker": "ACN",   "name": "Accenture"},
    {"ticker": "ABT",   "name": "Abbott Laboratories"},
    {"ticker": "MCD",   "name": "McDonald's Corporation"},
    {"ticker": "DHR",   "name": "Danaher Corporation"},
    {"ticker": "NEE",   "name": "NextEra Energy"},
    {"ticker": "TXN",   "name": "Texas Instruments"},
    {"ticker": "QCOM",  "name": "Qualcomm Inc."},
    {"ticker": "AMD",   "name": "Advanced Micro Devices"},
    {"ticker": "INTU",  "name": "Intuit Inc."},
    {"ticker": "AMGN",  "name": "Amgen Inc."},
    {"ticker": "RTX",   "name": "Raytheon Technologies"},
    {"ticker": "HON",   "name": "Honeywell International"},
    {"ticker": "IBM",   "name": "International Business Machines"},
    {"ticker": "GS",    "name": "Goldman Sachs"},
    {"ticker": "MS",    "name": "Morgan Stanley"},
    {"ticker": "BAC",   "name": "Bank of America"},
    {"ticker": "WFC",   "name": "Wells Fargo"},
    {"ticker": "C",     "name": "Citigroup Inc."},
    {"ticker": "BLK",   "name": "BlackRock Inc."},
    {"ticker": "SPGI",  "name": "S&P Global"},
    {"ticker": "AXP",   "name": "American Express"},
    {"ticker": "SCHW",  "name": "Charles Schwab"},
    {"ticker": "USB",   "name": "U.S. Bancorp"},
    {"ticker": "NFLX",  "name": "Netflix Inc."},
    {"ticker": "DIS",   "name": "Walt Disney Company"},
    {"ticker": "CMCSA", "name": "Comcast Corporation"},
    {"ticker": "T",     "name": "AT&T Inc."},
    {"ticker": "VZ",    "name": "Verizon Communications"},
    {"ticker": "TMUS",  "name": "T-Mobile US"},
    {"ticker": "UBER",  "name": "Uber Technologies"},
    {"ticker": "LYFT",  "name": "Lyft Inc."},
    {"ticker": "ABNB",  "name": "Airbnb Inc."},
    {"ticker": "SNAP",  "name": "Snap Inc."},
    {"ticker": "SPOT",  "name": "Spotify Technology"},
    {"ticker": "SQ",    "name": "Block Inc."},
    {"ticker": "PYPL",  "name": "PayPal Holdings"},
    {"ticker": "SHOP",  "name": "Shopify Inc."},
    {"ticker": "CRM",   "name": "Salesforce Inc."},
    {"ticker": "ORCL",  "name": "Oracle Corporation"},
    {"ticker": "SAP",   "name": "SAP SE"},
    {"ticker": "NOW",   "name": "ServiceNow Inc."},
    {"ticker": "SNOW",  "name": "Snowflake Inc."},
    {"ticker": "PLTR",  "name": "Palantir Technologies"},
    {"ticker": "NET",   "name": "Cloudflare Inc."},
    {"ticker": "ZS",    "name": "Zscaler Inc."},
    {"ticker": "CRWD",  "name": "CrowdStrike Holdings"},
    {"ticker": "DDOG",  "name": "Datadog Inc."},
    {"ticker": "MDB",   "name": "MongoDB Inc."},
    {"ticker": "COIN",  "name": "Coinbase Global"},
    {"ticker": "HOOD",  "name": "Robinhood Markets"},
    {"ticker": "BA",    "name": "Boeing Company"},
    {"ticker": "CAT",   "name": "Caterpillar Inc."},
    {"ticker": "GE",    "name": "GE Aerospace"},
    {"ticker": "MMM",   "name": "3M Company"},
    {"ticker": "DE",    "name": "Deere & Company"},
    {"ticker": "LMT",   "name": "Lockheed Martin"},
    {"ticker": "NOC",   "name": "Northrop Grumman"},
    {"ticker": "F",     "name": "Ford Motor Company"},
    {"ticker": "GM",    "name": "General Motors"},
    {"ticker": "RIVN",  "name": "Rivian Automotive"},
    {"ticker": "LCID",  "name": "Lucid Group"},
    {"ticker": "NIO",   "name": "NIO Inc."},
    {"ticker": "PFE",   "name": "Pfizer Inc."},
    {"ticker": "MRNA",  "name": "Moderna Inc."},
    {"ticker": "BNTX",  "name": "BioNTech SE"},
    {"ticker": "GILD",  "name": "Gilead Sciences"},
    {"ticker": "BIIB",  "name": "Biogen Inc."},
    {"ticker": "REGN",  "name": "Regeneron Pharmaceuticals"},
    {"ticker": "VRTX",  "name": "Vertex Pharmaceuticals"},
    {"ticker": "SPY",   "name": "SPDR S&P 500 ETF"},
    {"ticker": "QQQ",   "name": "Invesco QQQ Trust"},
    {"ticker": "VTI",   "name": "Vanguard Total Stock Market ETF"},
]


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _load_profile(user_id: str) -> UserProfile:
    """Load investor profile from DB; return safe defaults if not found."""
    try:
        resp = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
        if resp.data:
            return UserProfile.from_dict({**resp.data[0], "user_id": user_id})
    except Exception:
        pass
    return UserProfile(user_id=user_id)


# ── Existing endpoints (unchanged) ────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "FinSight API running", "version": "2.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/search")
async def search_stocks(q: str = ""):
    if not q or len(q) < 1:
        return []
    try:
        import yfinance as yf
        search  = yf.Search(q, max_results=10, enable_fuzzy_query=True)
        quotes  = search.quotes or []
        results = []
        for item in quotes:
            ticker     = item.get("symbol", "")
            name       = item.get("longname") or item.get("shortname") or ""
            exchange   = item.get("exchange", "")
            quote_type = item.get("quoteType", "")
            if quote_type in ["EQUITY", "ETF"] and ticker and name:
                results.append({"ticker": ticker, "name": name,
                                 "exchange": exchange, "type": quote_type})
        if results:
            return results[:8]
    except Exception:
        pass
    from difflib import SequenceMatcher
    def score(item, q):
        ql = q.lower()
        return max(
            SequenceMatcher(None, ql, item["ticker"].lower()).ratio(),
            SequenceMatcher(None, ql, item["name"].lower()).ratio(),
            1.0 if item["ticker"].lower().startswith(ql) else 0.0,
            0.8 if item["name"].lower().startswith(ql) else 0.0,
        )
    ranked = sorted([(s, score(s, q)) for s in STOCKS], key=lambda x: x[1], reverse=True)
    return [s for s, sc in ranked if sc > 0.3][:8]


@app.get("/chart/{ticker}")
async def get_chart_data(ticker: str, period: str = "1M"):
    try:
        import yfinance as yf
        period_map   = {"1D":"1d","1W":"5d","1M":"1mo","3M":"3mo","6M":"6mo","1Y":"1y","5Y":"5y","MAX":"max"}
        interval_map = {"1D":"5m","1W":"1h","1M":"1d","3M":"1d","6M":"1d","1Y":"1d","5Y":"1wk","MAX":"1mo"}
        hist = yf.Ticker(ticker.upper()).history(
            period   = period_map.get(period, "1mo"),
            interval = interval_map.get(period, "1d"),
        )
        if hist.empty:
            raise HTTPException(status_code=404, detail="No data found")
        data = [
            {"date": str(d), "close": round(float(r["Close"]),2),
             "open": round(float(r["Open"]),2), "high": round(float(r["High"]),2),
             "low": round(float(r["Low"]),2), "volume": int(r["Volume"])}
            for d, r in hist.iterrows()
        ]
        first, last = data[0]["close"], data[-1]["close"]
        chg = round(((last - first) / first) * 100, 2) if first else 0
        return {"ticker": ticker.upper(), "period": period, "data": data,
                "change_pct": chg, "is_positive": chg >= 0}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── /analyze — now async + personalised ───────────────────────────────────────

@app.post("/analyze")
async def analyze_stock(
    request: AnalyzeRequest,
    current_user=Depends(get_current_user),
):
    ticker = request.ticker.upper().strip()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    # Raises 429 if over daily limit (same behaviour as v1)
    check_usage_limit(current_user.id)

    profile = await _load_profile(current_user.id)

    try:
        # Direct await — no run_in_executor needed, orchestrator is async-native
        result = await run_orchestrator_async(ticker, profile)

        if result.get("status") != "success":
            raise HTTPException(status_code=500, detail="Analysis failed")

        # Only count fresh analyses, not cache hits
        if not result.get("from_cache"):
            increment_usage(current_user.id)
            log_analysis(
                user_id        = current_user.id,
                ticker         = ticker,
                recommendation = result["recommendation"]["recommendation"],
                confidence     = result["recommendation"]["confidence_score"],
                elapsed        = result["elapsed_seconds"],
            )

        # Strip raw price_history — large DataFrame, frontend doesn't need it
        result.get("agent_results", {}).get("financial", {}).get("raw_data", {}).pop("price_history", None)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── /analyze/stream — NEW ─────────────────────────────────────────────────────

@app.post("/analyze/stream")
async def analyze_stream(
    request: AnalyzeRequest,
    current_user=Depends(get_current_user),
):
    """
    SSE streaming endpoint. Frontend gets progress + tokens as Claude generates.

    React fetch pattern:
        const resp = await fetch('/analyze/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json',
                     'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ ticker: 'AAPL' }),
        });
        const reader = resp.body.getReader();
        // read chunks, parse "data: {...}" lines
    """
    ticker = request.ticker.upper().strip()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    check_usage_limit(current_user.id)
    profile = await _load_profile(current_user.id)

    logged = False

    async def generate():
        nonlocal logged
        async for chunk in stream_analysis(ticker, profile):
            parsed = json.loads(chunk)
            if parsed.get("type") == "complete" and not logged:
                data = parsed.get("data", {})
                if not data.get("from_cache"):
                    logged = True
                    increment_usage(current_user.id)
                    log_analysis(
                        user_id        = current_user.id,
                        ticker         = ticker,
                        recommendation = data["recommendation"]["recommendation"],
                        confidence     = data["recommendation"]["confidence_score"],
                        elapsed        = data.get("elapsed_seconds", 0),
                    )
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        generate(),
        media_type = "text/event-stream",
        headers    = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── /profile — NEW ────────────────────────────────────────────────────────────

@app.get("/profile")
async def get_profile(current_user=Depends(get_current_user)):
    try:
        resp = supabase.table("user_profiles").select("*").eq(
            "user_id", current_user.id
        ).execute()
        if resp.data:
            return resp.data[0]
        return {
            "experience": "beginner", "goal": "grow_savings",
            "monthly_investable": "200_500", "risk_tolerance": "medium",
            "onboarding_complete": False,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/profile")
async def save_profile(
    request: ProfileRequest,
    current_user=Depends(get_current_user),
):
    data = {
        "user_id":            current_user.id,
        "experience":         request.experience,
        "goal":               request.goal,
        "monthly_investable": request.monthly_investable,
        "risk_tolerance":     request.risk_tolerance,
        "onboarding_complete": True,
    }
    try:
        supabase.table("user_profiles").upsert(data, on_conflict="user_id").execute()
        return {"status": "saved", **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── /watchlist — NEW ──────────────────────────────────────────────────────────

@app.get("/watchlist")
async def get_watchlist(current_user=Depends(get_current_user)):
    try:
        resp = supabase.table("watchlist").select("*").eq(
            "user_id", current_user.id
        ).order("created_at", desc=True).execute()
        return resp.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/watchlist")
async def add_watchlist(
    request: WatchlistRequest,
    current_user=Depends(get_current_user),
):
    ticker = request.ticker.upper().strip()
    # Free tier: max 5 tickers
    from backend.auth import get_user_profile
    prof = get_user_profile(current_user.id)
    if prof.get("tier") == "free":
        existing = supabase.table("watchlist").select("id").eq(
            "user_id", current_user.id
        ).execute()
        if len(existing.data or []) >= 5:
            raise HTTPException(
                status_code=403,
                detail="Free tier: max 5 watchlist items. Upgrade for unlimited."
            )
    try:
        supabase.table("watchlist").upsert(
            {"user_id": current_user.id, "ticker": ticker},
            on_conflict="user_id,ticker",
        ).execute()
        return {"status": "added", "ticker": ticker}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/watchlist/{ticker}")
async def remove_watchlist(ticker: str, current_user=Depends(get_current_user)):
    try:
        supabase.table("watchlist").delete().eq(
            "user_id", current_user.id
        ).eq("ticker", ticker.upper()).execute()
        return {"status": "removed", "ticker": ticker.upper()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/watchlist/brief")
async def watchlist_brief(current_user=Depends(get_current_user)):
    """
    Returns latest cached analysis for all watchlist tickers.
    Scheduler pre-computes at 07:30 UTC, so this is near-instant.
    """
    profile = await _load_profile(current_user.id)
    try:
        resp    = supabase.table("watchlist").select("ticker").eq(
            "user_id", current_user.id
        ).execute()
        tickers = [r["ticker"] for r in (resp.data or [])]
    except Exception:
        tickers = []

    items = []
    for t in tickers:
        try:
            r   = await run_orchestrator_async(t, profile)
            rec = r.get("recommendation", {})
            items.append({
                "ticker":         t,
                "company_name":   r.get("company_name", t),
                "current_price":  r.get("current_price"),
                "recommendation": rec.get("recommendation"),
                "confidence":     rec.get("confidence_score"),
                "thesis_snippet": (rec.get("thesis", "")[:120] + "…") if rec.get("thesis") else "",
                "from_cache":     r.get("from_cache", False),
            })
        except Exception as e:
            items.append({"ticker": t, "error": str(e)})

    return {"items": items, "count": len(items)}


# ── Existing endpoints (unchanged) ────────────────────────────────────────────

@app.get("/me")
def get_me(current_user=Depends(get_current_user)):
    from backend.auth import get_user_profile
    profile = get_user_profile(current_user.id)
    return {
        "id":                  current_user.id,
        "email":               current_user.email,
        "tier":                profile.get("tier", "free"),
        "analyses_today":      profile.get("analyses_today", 0),
        "daily_limit":         int(os.getenv("FREE_TIER_DAILY_LIMIT", 3))
                               if profile.get("tier") == "free" else None,
        "onboarding_complete": profile.get("onboarding_complete", False),
    }

@app.get("/history")
def get_history(current_user=Depends(get_current_user)):
    result = supabase.table("usage_logs").select("*").eq(
        "user_id", current_user.id
    ).order("created_at", desc=True).limit(50).execute()
    return result.data

@app.post("/create-checkout")
def create_checkout(current_user=Depends(get_current_user)):
    return {"checkout_url": create_checkout_session(current_user.id, current_user.email)}

@app.post("/create-portal")
def create_portal(current_user=Depends(get_current_user)):
    return {"portal_url": create_portal_session(current_user.id)}

@app.post("/webhook")
async def stripe_webhook(request: Request):
    return await handle_webhook(request)

@app.get("/reports/{ticker}")
async def get_report(ticker: str, current_user=Depends(get_current_user)):
    path = f"./output/reports/{ticker.upper()}_report.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No report found for {ticker}")
    with open(path) as f:
        return json.load(f)