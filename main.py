import sys
from agents.orchestrator import run_orchestrator

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py TICKER")
        print("Example: python main.py AAPL")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    result = run_orchestrator(ticker)

    rec = result["recommendation"]
    signals = result["signals"]

    print(f"""
╔══════════════════════════════════════════════════╗
║           FINSIGHT INVESTMENT BRIEF              ║
╚══════════════════════════════════════════════════╝

  Company:     {result["company_name"]} ({result["ticker"]})
  Price:       ${result["current_price"]}

  AGENT SIGNALS:
  • Fundamental:  {signals["financial"]}
  • Sentiment:    {signals["sentiment"]}
  • Technical:    {signals["technical"]}
  • SEC Filings:  {signals["sec"]}

  ══════════════════════════════════════════════════
  RECOMMENDATION:  {rec["recommendation"]}
  Confidence:      {rec["confidence_score"]}
  Horizon:         {rec["investment_horizon"]}
  Upside:          {rec["price_target_upside"]}
  ══════════════════════════════════════════════════

  THESIS:
  {rec["thesis"]}

  BULL CASE:
  {rec["bull_case"]}

  BEAR CASE:
  {rec["bear_case"]}

  KEY CATALYSTS:
  {chr(10).join(f"  • {c}" for c in rec["key_catalysts"])}

  KEY RISKS:
  {chr(10).join(f"  • {r}" for r in rec["key_risks"])}

  POSITION SIZING:
  {rec["position_sizing"]}

  Generated in {result["elapsed_seconds"]}s
  Report saved to output/reports/{result["ticker"]}_report.json
""")

if __name__ == "__main__":
    main()