import anthropic
import json
import config
from tools.sec_fetcher import get_sec_filings_text
from tools.vector_store import get_sec_insights

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

def run_rag_agent(ticker: str) -> dict:
    print(f"\n[Agent 4/4] RAG Agent running for {ticker}...")
    try:
        filings_data = get_sec_filings_text(ticker)
        if filings_data.get("status") == "failed":
            return {"error": filings_data.get("error"), "status": "failed"}
        insights = get_sec_insights(ticker, filings_data)
        if insights.get("status") == "failed":
            return {"error": insights.get("error"), "status": "failed"}
        insights_text = ""
        for topic, content in insights["insights"].items():
            insights_text += f"\n{topic.upper()}:\n{content[:500]}\n"
        prompt = f"""You are a fundamental research analyst specializing in SEC filing analysis.
Based on excerpts from {ticker} SEC filings, provide a structured assessment.

{insights_text}

Provide your analysis in this exact JSON format:
{{
    "key_risk_factors": ["risk 1", "risk 2", "risk 3"],
    "growth_drivers": ["driver 1", "driver 2"],
    "management_tone": "one sentence on management confidence",
    "competitive_position": "one sentence on competitive moat",
    "red_flags": [],
    "positive_signals": ["signal 1", "signal 2"],
    "sec_signal": "BULLISH or BEARISH or NEUTRAL",
    "sec_confidence": 0.0,
    "sec_summary": "2-3 sentence summary of SEC filing insights"
}}
Return ONLY the JSON, no other text."""
        response = client.messages.create(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}]
        )
        try:
            analysis = json.loads(response.content[0].text)
        except json.JSONDecodeError:
            text = response.content[0].text
            text = text[text.find("{"):text.rfind("}")+1]
            analysis = json.loads(text)
        print(f"  [Agent 4/4] SEC signal: {analysis.get('sec_signal')}")
        return {
            "ticker": ticker,
            "filings_analyzed": filings_data["total_filings"],
            "chunks_indexed": insights["total_chunks_indexed"],
            "analysis": analysis,
            "status": "success"
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e), "status": "failed"}
