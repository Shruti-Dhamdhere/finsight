"""
agents/orchestrator.py — FinSight v2
=====================================
All 4 agents are plain `def` (confirmed). They run in a ThreadPoolExecutor
via run_in_executor so they don't block FastAPI's event loop.

financial + sentiment + rag  →  parallel via asyncio.gather  (~12-15s)
technical                    →  after financial (needs price_history) (~2s)
synthesis                    →  Claude with user profile injected      (~3s)
Total                        →  ~17-20s fresh  |  <100ms cached

Public API (drop-in for existing code):
    run_orchestrator(ticker)                   ← sync, same signature as v1
    run_orchestrator(ticker, profile)          ← sync + personalised
    run_orchestrator_async(ticker, profile)    ← native async for FastAPI
    stream_analysis(ticker, profile)           ← async generator for SSE
"""

import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncIterator, Optional

import anthropic
import config
from agents.financial_agent import run_financial_agent
from agents.sentiment_agent import run_sentiment_agent
from agents.technical_agent import run_technical_agent
from agents.rag_agent import run_rag_agent

client   = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
_pool    = ThreadPoolExecutor(max_workers=8)

# ── In-memory cache ────────────────────────────────────────────────────────────
# key → {"data": result_dict, "expires": float}
# TTL: 6 hours. Replace with Redis by swapping _cache_get/_cache_set.
_cache: dict = {}
CACHE_TTL    = 6 * 60 * 60


def _cache_get(key: str) -> Optional[dict]:
    entry = _cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    return None


def _cache_set(key: str, data: dict) -> None:
    _cache[key] = {"data": data, "expires": time.time() + CACHE_TTL}


# ── User profile ───────────────────────────────────────────────────────────────

class UserProfile:
    def __init__(
        self,
        experience:         str = "beginner",   # beginner|intermediate|experienced
        goal:               str = "grow_savings",# grow_savings|income|learn
        monthly_investable: str = "200_500",     # under_200|200_500|500_plus
        risk_tolerance:     str = "medium",      # low|medium|high
        user_id: Optional[str] = None,
    ):
        self.experience         = experience
        self.goal               = goal
        self.monthly_investable = monthly_investable
        self.risk_tolerance     = risk_tolerance
        self.user_id            = user_id

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        return cls(
            experience         = d.get("experience",         "beginner"),
            goal               = d.get("goal",               "grow_savings"),
            monthly_investable = d.get("monthly_investable", "200_500"),
            risk_tolerance     = d.get("risk_tolerance",     "medium"),
            user_id            = d.get("user_id"),
        )

    def cache_key(self, ticker: str) -> str:
        # Different profiles get different cached synthesis
        return f"{ticker}:{self.experience}:{self.risk_tolerance}"


# ── Async wrappers for sync agents ────────────────────────────────────────────
# Agents are plain `def` (confirmed by grep).
# run_in_executor moves them onto a thread so they don't block the event loop.

async def _run_financial(ticker: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_pool, run_financial_agent, ticker)

async def _run_sentiment(ticker: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_pool, run_sentiment_agent, ticker)

async def _run_rag(ticker: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_pool, run_rag_agent, ticker)

async def _run_technical(ticker: str, price_history) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_pool, run_technical_agent, ticker, price_history)


# ── Synthesis prompt ───────────────────────────────────────────────────────────

def _build_prompt(
    ticker:  str,
    results: dict,
    signals: dict,
    profile: UserProfile,
) -> str:
    fin     = results["financial"].get("analysis", {})
    sent    = results["sentiment"].get("analysis", {})
    tech    = results["technical"].get("analysis", {})
    rag     = results["rag"].get("analysis",  {})
    raw     = results["financial"].get("raw_data", {})
    fin_data = raw.get("financials", {})
    company  = raw.get("company",    {})

    exp_text = {
        "beginner":     "a complete beginner who has never invested before",
        "intermediate": "someone who has invested before and understands the basics",
        "experienced":  "an experienced investor comfortable with financial terminology",
    }.get(profile.experience, "a beginner")

    goal_text = {
        "grow_savings": "grow their savings over the long term",
        "income":       "generate regular income from investments",
        "learn":        "learn how investing works while getting started",
    }.get(profile.goal, "grow savings")

    risk_text = {
        "low":    "very risk-averse — they cannot afford to lose money",
        "medium": "moderately risk-tolerant — some ups and downs are fine",
        "high":   "risk-tolerant — willing to accept volatility for higher returns",
    }.get(profile.risk_tolerance, "moderate")

    budget_text = {
        "under_200": "less than $200/month",
        "200_500":   "$200–500/month",
        "500_plus":  "more than $500/month",
    }.get(profile.monthly_investable, "$200–500/month")

    is_beginner = profile.experience == "beginner"

    language_note = (
        "Use plain English. Avoid jargon. If you use a term like 'P/E ratio' "
        "or 'RSI', define it in brackets immediately after."
        if is_beginner else
        "Use standard financial terminology. Be precise and concise."
    )
    risk_note = (
        "\n- Emphasise capital preservation and downside risk prominently."
        if profile.risk_tolerance == "low" else ""
    )
    budget_note = (
        f"\n- In position_sizing, give concrete dollar amounts for someone "
        f"investing {budget_text}."
        if is_beginner else ""
    )

    return f"""You are the Chief Investment Officer at a top investment firm.
Four specialist analysts have submitted research on {ticker}.
Synthesise their findings into a final investment recommendation.

USER PROFILE — adapt your entire response to this person:
- Experience: {exp_text}
- Goal: They want to {goal_text}
- Monthly investment budget: {budget_text}
- Risk tolerance: {risk_text}

LANGUAGE INSTRUCTIONS:
- {language_note}{risk_note}{budget_note}

COMPANY: {company.get("name", ticker)} ({ticker})
CURRENT PRICE: ${fin_data.get("current_price", "N/A")}
SECTOR: {company.get("sector", "N/A")}

ANALYST SIGNALS:
- Fundamental: {signals["financial"]}
- Sentiment:   {signals["sentiment"]}
- Technical:   {signals["technical"]}
- SEC Filings: {signals["sec"]}

KEY FINDINGS:
Fundamentals: {fin.get("analyst_summary",  "N/A")}
Sentiment:    {sent.get("news_summary",    "N/A")}
Technical:    {tech.get("technical_summary","N/A")}
SEC Filings:  {rag.get("sec_summary",      "N/A")}

STRENGTHS:  {fin.get("key_strengths",        [])}
CONCERNS:   {fin.get("key_concerns",         [])}
RISKS:      {rag.get("key_risk_factors",     [])}
CATALYSTS:  {rag.get("growth_drivers",       [])}

Return ONLY this JSON, no other text:
{{
    "recommendation":      "BUY or HOLD or SELL",
    "confidence_score":    0.0,
    "price_target_upside": "X% upside/downside from current price",
    "investment_horizon":  "short-term or medium-term or long-term",
    "thesis":              "3-4 sentences at the user's reading level",
    "bull_case":           "2 sentences — plain English if beginner",
    "bear_case":           "2 sentences — plain English if beginner",
    "key_catalysts":       ["catalyst 1", "catalyst 2", "catalyst 3"],
    "key_risks":           ["risk 1", "risk 2", "risk 3"],
    "position_sizing":     "Concrete advice for this user's budget and risk tolerance",
    "beginner_summary":    "If experience=beginner: 2 plain-English sentences on what to actually do. Otherwise empty string."
}}"""


# ── Core async orchestrator ────────────────────────────────────────────────────

async def run_orchestrator_async(
    ticker:  str,
    profile: Optional[UserProfile] = None,
) -> dict:
    ticker  = ticker.upper().strip()
    profile = profile or UserProfile()
    key     = profile.cache_key(ticker)
    start   = time.time()

    # Cache hit — return immediately
    cached = _cache_get(key)
    if cached:
        result = dict(cached)           # shallow copy so we don't mutate cache
        result["from_cache"]      = True
        result["elapsed_seconds"] = round(time.time() - start, 3)
        print(f"[Orchestrator] Cache HIT {key} — {result['elapsed_seconds']}s")
        return result

    print(f"[Orchestrator] START {ticker} | {profile.experience}/{profile.risk_tolerance}")

    errors  = {}
    results = {}

    # ── Phase 1: financial + sentiment + rag in parallel ──────────────────────
    fin_r, sent_r, rag_r = await asyncio.gather(
        _run_financial(ticker),
        _run_sentiment(ticker),
        _run_rag(ticker),
        return_exceptions=True,
    )

    for name, r in [("financial", fin_r), ("sentiment", sent_r), ("rag", rag_r)]:
        if isinstance(r, Exception):
            errors[name] = str(r)
            results[name] = {"status": "failed", "analysis": {}, "raw_data": {}}
            print(f"[Orchestrator] {name} FAILED: {r}")
        else:
            results[name] = r

    t1 = round(time.time() - start, 1)
    print(f"[Orchestrator] Phase 1 done in {t1}s")

    # ── Phase 2: technical — needs price_history from financial ───────────────
    # price_history confirmed at raw_data["price_history"] in data_fetcher.py
    price_history = results["financial"].get("raw_data", {}).get("price_history")
    try:
        results["technical"] = await _run_technical(ticker, price_history)
    except Exception as e:
        errors["technical"] = str(e)
        results["technical"] = {"status": "failed", "analysis": {}}
        print(f"[Orchestrator] technical FAILED: {e}")

    t2 = round(time.time() - start, 1)
    print(f"[Orchestrator] Phase 2 done in {t2}s")

    # ── Phase 3: signals ───────────────────────────────────────────────────────
    signals = {
        "financial": results["financial"].get("analysis", {}).get("fundamental_signal", "NEUTRAL"),
        "sentiment": results["sentiment"].get("analysis", {}).get("sentiment_signal",   "NEUTRAL"),
        "technical": results["technical"].get("analysis", {}).get("technical_signal",   "NEUTRAL"),
        "sec":       results["rag"].get("analysis",       {}).get("sec_signal",         "NEUTRAL"),
    }
    print(f"[Orchestrator] Signals: {signals}")

    # ── Phase 4: synthesis with user profile ──────────────────────────────────
    prompt   = _build_prompt(ticker, results, signals, profile)
    response = client.messages.create(
        model      = config.MODEL,
        max_tokens = config.MAX_TOKENS,
        messages   = [{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    try:
        recommendation = json.loads(raw_text)
    except json.JSONDecodeError:
        recommendation = json.loads(raw_text[raw_text.find("{"):raw_text.rfind("}") + 1])

    elapsed  = round(time.time() - start, 1)
    raw_data = results["financial"].get("raw_data", {})

    final = {
        "ticker":        ticker,
        "company_name":  raw_data.get("company",    {}).get("name",          ticker),
        "current_price": raw_data.get("financials", {}).get("current_price", "N/A"),
        "signals":       signals,
        "recommendation": recommendation,
        "agent_results": results,
        "elapsed_seconds": elapsed,
        "errors":        errors,
        "status":        "success",
        "from_cache":    False,
        "user_profile": {
            "experience":    profile.experience,
            "goal":          profile.goal,
            "risk_tolerance": profile.risk_tolerance,
        },
    }

    _cache_set(key, final)

    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    with open(f"{config.REPORTS_DIR}/{ticker}_report.json", "w") as f:
        json.dump(final, f, indent=2, default=str)

    print(f"[Orchestrator] DONE {ticker} in {elapsed}s — cached 6h")
    return final


# ── Streaming generator for SSE ───────────────────────────────────────────────

async def stream_analysis(
    ticker:  str,
    profile: Optional[UserProfile] = None,
) -> AsyncIterator[str]:
    """
    Yields newline-delimited JSON strings for Server-Sent Events.

    Sequence:
      {"type":"status",     "message":"Analysing AAPL…"}
      {"type":"agent_done", "agent":"financial"}
      {"type":"agent_done", "agent":"sentiment"}
      {"type":"agent_done", "agent":"rag"}
      {"type":"agent_done", "agent":"technical"}
      {"type":"signals",    "data":{…}}
      {"type":"token",      "text":"…"}   ← repeats as Claude streams
      {"type":"complete",   "data":{…}}
    """
    ticker  = ticker.upper().strip()
    profile = profile or UserProfile()
    key     = profile.cache_key(ticker)

    # Cache hit
    cached = _cache_get(key)
    if cached:
        result = dict(cached)
        result["from_cache"] = True
        yield json.dumps({"type": "complete", "data": result})
        return

    yield json.dumps({"type": "status", "message": f"Analysing {ticker}…"})

    errors  = {}
    results = {}

    # Phase 1: parallel
    fin_r, sent_r, rag_r = await asyncio.gather(
        _run_financial(ticker),
        _run_sentiment(ticker),
        _run_rag(ticker),
        return_exceptions=True,
    )

    for name, r in [("financial", fin_r), ("sentiment", sent_r), ("rag", rag_r)]:
        if isinstance(r, Exception):
            errors[name] = str(r)
            results[name] = {"status": "failed", "analysis": {}, "raw_data": {}}
        else:
            results[name] = r
        yield json.dumps({"type": "agent_done", "agent": name})

    # Phase 2: technical
    price_history = results["financial"].get("raw_data", {}).get("price_history")
    try:
        results["technical"] = await _run_technical(ticker, price_history)
    except Exception as e:
        errors["technical"] = str(e)
        results["technical"] = {"status": "failed", "analysis": {}}
    yield json.dumps({"type": "agent_done", "agent": "technical"})

    signals = {
        "financial": results["financial"].get("analysis", {}).get("fundamental_signal", "NEUTRAL"),
        "sentiment": results["sentiment"].get("analysis", {}).get("sentiment_signal",   "NEUTRAL"),
        "technical": results["technical"].get("analysis", {}).get("technical_signal",   "NEUTRAL"),
        "sec":       results["rag"].get("analysis",       {}).get("sec_signal",         "NEUTRAL"),
    }
    yield json.dumps({"type": "signals", "data": signals})

    # Phase 3: streaming synthesis
    prompt    = _build_prompt(ticker, results, signals, profile)
    full_text = ""

    with client.messages.stream(
        model      = config.MODEL,
        max_tokens = config.MAX_TOKENS,
        messages   = [{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            full_text += text
            yield json.dumps({"type": "token", "text": text})

    try:
        recommendation = json.loads(full_text)
    except json.JSONDecodeError:
        recommendation = json.loads(full_text[full_text.find("{"):full_text.rfind("}") + 1])

    raw_data = results["financial"].get("raw_data", {})
    final = {
        "ticker":        ticker,
        "company_name":  raw_data.get("company",    {}).get("name",          ticker),
        "current_price": raw_data.get("financials", {}).get("current_price", "N/A"),
        "signals":       signals,
        "recommendation": recommendation,
        "agent_results": results,
        "errors":        errors,
        "status":        "success",
        "from_cache":    False,
        "user_profile": {
            "experience":    profile.experience,
            "goal":          profile.goal,
            "risk_tolerance": profile.risk_tolerance,
        },
    }

    _cache_set(key, final)
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    with open(f"{config.REPORTS_DIR}/{ticker}_report.json", "w") as f:
        json.dump(final, f, indent=2, default=str)

    yield json.dumps({"type": "complete", "data": final})


# ── Sync wrapper — backward compat only ───────────────────────────────────────
# backend/main.py now calls run_orchestrator_async directly.
# This wrapper exists only if something else calls run_orchestrator() sync.

def run_orchestrator(ticker: str, profile: Optional[UserProfile] = None) -> dict:
    return asyncio.run(run_orchestrator_async(ticker, profile))