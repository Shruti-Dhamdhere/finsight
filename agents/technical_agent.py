import anthropic
import json
import config
from tools.data_fetcher import get_stock_data
from tools.technical_indicators import calculate_indicators

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

def run_technical_agent(ticker: str, price_history=None) -> dict:
    print(f"\n[Agent 3/4] Technical Agent running for {ticker}...")
    try:
        if price_history is None:
            raw_data = get_stock_data(ticker)
            price_history = raw_data["price_history"]
        indicators = calculate_indicators(price_history)
        if indicators.get("status") == "failed":
            return {"error": indicators.get("error"), "status": "failed"}
        tech_summary = f"""
RSI: {indicators["rsi"]}
MACD: {indicators["macd"]["macd"]} | Signal: {indicators["macd"]["signal"]} | Histogram: {indicators["macd"]["histogram"]}
Bollinger Position: {indicators["bollinger_bands"]["position_pct"]}%
SMA 20/50/200: {indicators["moving_averages"]["sma_20"]} / {indicators["moving_averages"]["sma_50"]} / {indicators["moving_averages"]["sma_200"]}
Volume Ratio: {indicators["volume"]["ratio"]}x
52W High/Low: {indicators["support_resistance"]["52w_high"]} / {indicators["support_resistance"]["52w_low"]}
Signals: {indicators["bullish_count"]} bullish, {indicators["bearish_count"]} bearish
Overall: {indicators["overall_signal"]}
"""
        prompt = f"""You are a technical analyst with 20 years of experience.
Analyze these technical indicators for {ticker}.

{tech_summary}

Provide your analysis in this exact JSON format:
{{
    "trend_assessment": "one sentence on current price trend",
    "momentum_assessment": "one sentence on momentum",
    "support_level": 0.0,
    "resistance_level": 0.0,
    "technical_signal": "BULLISH or BEARISH or NEUTRAL",
    "technical_confidence": 0.0,
    "key_levels_to_watch": ["level 1", "level 2"],
    "technical_summary": "2-3 sentence overall technical assessment"
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
        print(f"  [Agent 3/4] Technical signal: {analysis.get('technical_signal')}")
        return {"ticker": ticker, "indicators": indicators, "analysis": analysis, "status": "success"}
    except Exception as e:
        return {"ticker": ticker, "error": str(e), "status": "failed"}
