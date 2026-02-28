import anthropic
import json
import config
from tools.data_fetcher import get_stock_data, format_large_number

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def run_financial_agent(ticker: str) -> dict:
    """
    Financial Agent: fetches and analyzes fundamental data.
    Uses Claude to interpret raw financials into investment insights.
    """
    print(f"\n[Agent 1/4] Financial Agent running for {ticker}...")

    # Step 1: Fetch raw data
    raw_data = get_stock_data(ticker)

    if raw_data.get("status") == "failed":
        return {"error": raw_data.get("error"), "status": "failed"}

    # Step 2: Format financials for Claude
    fin = raw_data["financials"]
    perf = raw_data["performance"]
    company = raw_data["company"]

    financial_summary = f"""
COMPANY: {company['name']} ({ticker})
SECTOR: {company['sector']} | INDUSTRY: {company['industry']}

PRICE METRICS:
- Current Price: ${fin['current_price']}
- Day Change: {fin['day_change_pct']}%
- 52-Week High: {fin['52_week_high']} | Low: {fin['52_week_low']}
- Analyst Target: {fin['analyst_target_price']}
- Analyst Recommendation: {fin['recommendation']}

PERFORMANCE vs BENCHMARK (SPY):
- 1 Week: {perf['1_week']}% 
- 1 Month: {perf['1_month']}%
- 1 Year: {perf['1_year']}% vs SPY: {raw_data['benchmark_1yr_return']}%

VALUATION:
- Market Cap: {format_large_number(fin['market_cap'])}
- P/E Ratio: {fin['pe_ratio']}
- Forward P/E: {fin['forward_pe']}
- EPS: {fin['eps']}

FINANCIAL HEALTH:
- Revenue: {format_large_number(fin['revenue'])}
- Revenue Growth: {fin['revenue_growth']}
- Gross Margins: {fin['gross_margins']}
- Profit Margins: {fin['profit_margins']}
- Debt/Equity: {fin['debt_to_equity']}
- Return on Equity: {fin['return_on_equity']}
- Free Cash Flow: {format_large_number(fin['free_cashflow'])}
- Dividend Yield: {fin['dividend_yield']}

VOLATILITY: {raw_data['volatility_annualized_pct']}% annualized
"""

    # Step 3: Claude analyzes the fundamentals
    prompt = f"""You are a senior equity research analyst at a top investment bank.
Analyze the following fundamental data for {ticker} and provide a concise assessment.

{financial_summary}

Provide your analysis in this exact JSON format:
{{
    "valuation_assessment": "one sentence on whether stock is cheap/fair/expensive",
    "financial_health_score": "1-10 score with one sentence explanation",
    "growth_outlook": "one sentence on growth prospects",
    "key_strengths": ["strength 1", "strength 2", "strength 3"],
    "key_concerns": ["concern 1", "concern 2"],
    "fundamental_signal": "BULLISH or BEARISH or NEUTRAL",
    "fundamental_confidence": 0.0,
    "analyst_summary": "2-3 sentence overall fundamental assessment"
}}

Return ONLY the JSON, no other text."""

    response = client.messages.create(
        model=config.MODEL,
        max_tokens=config.MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse Claude's response
    try:
        analysis = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        # Clean and retry parse
        text = response.content[0].text
        text = text[text.find("{"):text.rfind("}") + 1]
        analysis = json.loads(text)

    print(f"  [Agent 1/4] Fundamental signal: {analysis.get('fundamental_signal')}")

    return {
        "ticker": ticker,
        "raw_data": raw_data,
        "analysis": analysis,
        "financial_summary": financial_summary,
        "status": "success"
    }