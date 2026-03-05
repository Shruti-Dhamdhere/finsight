import anthropic
import json
import time
import os
import config
from agents.financial_agent import run_financial_agent
from agents.sentiment_agent import run_sentiment_agent
from agents.technical_agent import run_technical_agent
from agents.rag_agent import run_rag_agent

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def run_orchestrator(ticker: str) -> dict:
    ticker = ticker.upper().strip()
    start_time = time.time()

    print(f"\n{'='*50}")
    print(f"  FinSight Research Agent: {ticker}")
    print(f"{'='*50}")

    results = {}
    errors = []

    try:
        results["financial"] = run_financial_agent(ticker)
    except Exception as e:
        errors.append(f"Financial agent failed: {e}")
        results["financial"] = {"status": "failed"}

    try:
        results["sentiment"] = run_sentiment_agent(ticker)
    except Exception as e:
        errors.append(f"Sentiment agent failed: {e}")
        results["sentiment"] = {"status": "failed"}

    try:
        price_history = results["financial"].get("raw_data", {}).get("price_history")
        results["technical"] = run_technical_agent(ticker, price_history)
    except Exception as e:
        errors.append(f"Technical agent failed: {e}")
        results["technical"] = {"status": "failed"}

    try:
        results["rag"] = run_rag_agent(ticker)
    except Exception as e:
        errors.append(f"RAG agent failed: {e}")
        results["rag"] = {"status": "failed"}

    signals = {
        "financial": results["financial"].get("analysis", {}).get("fundamental_signal", "NEUTRAL"),
        "sentiment": results["sentiment"].get("analysis", {}).get("sentiment_signal", "NEUTRAL"),
        "technical": results["technical"].get("analysis", {}).get("technical_signal", "NEUTRAL"),
        "sec": results["rag"].get("analysis", {}).get("sec_signal", "NEUTRAL")
    }

    print(f"\n[Synthesis] All signals collected: {signals}")
    print(f"[Synthesis] Generating final investment brief...")

    fin_analysis = results["financial"].get("analysis", {})
    sent_analysis = results["sentiment"].get("analysis", {})
    tech_analysis = results["technical"].get("analysis", {})
    rag_analysis = results["rag"].get("analysis", {})
    raw_data = results["financial"].get("raw_data", {})
    financials = raw_data.get("financials", {})
    company = raw_data.get("company", {})

    synthesis_prompt = f"""You are the Chief Investment Officer at a top hedge fund.
You have received research reports from 4 specialized analysts on {ticker}.
Synthesize their findings into a final investment recommendation.

COMPANY: {company.get("name", ticker)} ({ticker})
CURRENT PRICE: ${financials.get("current_price", "N/A")}
SECTOR: {company.get("sector", "N/A")}

ANALYST SIGNALS:
- Fundamental: {signals["financial"]}
- Sentiment: {signals["sentiment"]}
- Technical: {signals["technical"]}
- SEC Filings: {signals["sec"]}

KEY FINDINGS:
Fundamentals: {fin_analysis.get("analyst_summary", "N/A")}
Sentiment: {sent_analysis.get("news_summary", "N/A")}
Technical: {tech_analysis.get("technical_summary", "N/A")}
SEC Filings: {rag_analysis.get("sec_summary", "N/A")}

STRENGTHS: {fin_analysis.get("key_strengths", [])}
CONCERNS: {fin_analysis.get("key_concerns", [])}
RISKS: {rag_analysis.get("key_risk_factors", [])}
CATALYSTS: {rag_analysis.get("growth_drivers", [])}

Provide final recommendation in this exact JSON format:
{{
    "recommendation": "BUY or HOLD or SELL",
    "confidence_score": 0.0,
    "price_target_upside": "X% upside/downside from current price",
    "investment_horizon": "short-term or medium-term or long-term",
    "thesis": "3-4 sentence core investment thesis",
    "bull_case": "2 sentence bull case scenario",
    "bear_case": "2 sentence bear case scenario",
    "key_catalysts": ["catalyst 1", "catalyst 2", "catalyst 3"],
    "key_risks": ["risk 1", "risk 2", "risk 3"],
    "position_sizing": "small/medium/large position with reasoning"
}}
Return ONLY the JSON, no other text."""

    response = client.messages.create(
        model=config.MODEL,
        max_tokens=config.MAX_TOKENS,
        messages=[{"role": "user", "content": synthesis_prompt}]
    )

    try:
        recommendation = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        text = response.content[0].text
        text = text[text.find("{"):text.rfind("}")+1]
        recommendation = json.loads(text)

    elapsed = round(time.time() - start_time, 1)

    final_result = {
        "ticker": ticker,
        "company_name": company.get("name", ticker),
        "current_price": financials.get("current_price", "N/A"),
        "signals": signals,
        "recommendation": recommendation,
        "agent_results": results,
        "elapsed_seconds": elapsed,
        "errors": errors,
        "status": "success"
    }

    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    report_path = f"{config.REPORTS_DIR}/{ticker}_report.json"
    with open(report_path, "w") as f:
        json.dump(final_result, f, indent=2, default=str)

    print(f"[Synthesis] Done in {elapsed}s | Saved to {report_path}")
    return final_result