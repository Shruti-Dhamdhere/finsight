import anthropic
import json
import yfinance as yf
import config

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

def run_sentiment_agent(ticker: str) -> dict:
    print(f"\n[Agent 2/4] Sentiment Agent running for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news[:10] if stock.news else []
        news_text = ""
        for i, item in enumerate(news_items):
            title = item.get("content", {}).get("title", "")
            summary = item.get("content", {}).get("summary", "")
            pub_date = item.get("content", {}).get("pubDate", "")
            if title:
                news_text += f"{i+1}. [{pub_date}] {title}\n"
                if summary:
                    news_text += f"   {summary[:200]}\n"
        if not news_text:
            news_text = "No recent news available."
        prompt = f"""You are a sentiment analyst specializing in financial markets.
Analyze the following recent news for {ticker} and assess market sentiment.

RECENT NEWS:
{news_text}

Provide your analysis in this exact JSON format:
{{
    "overall_sentiment": "POSITIVE or NEGATIVE or NEUTRAL",
    "sentiment_score": 0.0,
    "news_summary": "2 sentence summary of key news themes",
    "positive_catalysts": ["catalyst 1", "catalyst 2"],
    "negative_risks": ["risk 1", "risk 2"],
    "media_tone": "one sentence on overall media tone",
    "sentiment_signal": "BULLISH or BEARISH or NEUTRAL",
    "sentiment_confidence": 0.0
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
        print(f"  [Agent 2/4] Sentiment signal: {analysis.get('sentiment_signal')}")
        return {"ticker": ticker, "news_count": len(news_items), "analysis": analysis, "status": "success"}
    except Exception as e:
        return {"ticker": ticker, "error": str(e), "status": "failed"}
