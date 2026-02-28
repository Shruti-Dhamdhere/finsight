import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import config

def get_stock_data(ticker: str) -> dict:
    """
    Fetch comprehensive stock data for a given ticker.
    Returns price history, company info, and key financials.
    """
    print(f"  [Financial Agent] Fetching data for {ticker}...")
    
    try:
        stock = yf.Ticker(ticker)
        
        # ─── Price History ────────────────────────────────────
        hist = stock.history(
            period=config.DEFAULT_PERIOD,
            interval=config.DEFAULT_INTERVAL
        )
        
        if hist.empty:
            return {"error": f"No price data found for {ticker}"}
        
        # ─── Current Price Metrics ────────────────────────────
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        price_change_pct = ((current_price - prev_price) / prev_price) * 100
        
        # ─── Price Performance ────────────────────────────────
        week_ago = hist['Close'].iloc[-5] if len(hist) >= 5 else hist['Close'].iloc[0]
        month_ago = hist['Close'].iloc[-21] if len(hist) >= 21 else hist['Close'].iloc[0]
        year_ago = hist['Close'].iloc[-252] if len(hist) >= 252 else hist['Close'].iloc[0]
        
        performance = {
            "1_week": round(((current_price - week_ago) / week_ago) * 100, 2),
            "1_month": round(((current_price - month_ago) / month_ago) * 100, 2),
            "1_year": round(((current_price - year_ago) / year_ago) * 100, 2),
        }
        
        # ─── Volatility ───────────────────────────────────────
        daily_returns = hist['Close'].pct_change().dropna()
        volatility_annualized = round(daily_returns.std() * np.sqrt(252) * 100, 2)
        
        # ─── Company Info ─────────────────────────────────────
        info = stock.info
        
        company_data = {
            "name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "country": info.get("country", "Unknown"),
            "employees": info.get("fullTimeEmployees", "N/A"),
            "description": info.get("longBusinessSummary", "N/A")[:500],
        }
        
        # ─── Key Financials ───────────────────────────────────
        financials = {
            "current_price": round(current_price, 2),
            "day_change_pct": round(price_change_pct, 2),
            "market_cap": info.get("marketCap", "N/A"),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "forward_pe": info.get("forwardPE", "N/A"),
            "eps": info.get("trailingEps", "N/A"),
            "revenue": info.get("totalRevenue", "N/A"),
            "revenue_growth": info.get("revenueGrowth", "N/A"),
            "gross_margins": info.get("grossMargins", "N/A"),
            "profit_margins": info.get("profitMargins", "N/A"),
            "debt_to_equity": info.get("debtToEquity", "N/A"),
            "return_on_equity": info.get("returnOnEquity", "N/A"),
            "free_cashflow": info.get("freeCashflow", "N/A"),
            "dividend_yield": info.get("dividendYield", "N/A"),
            "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
            "analyst_target_price": info.get("targetMeanPrice", "N/A"),
            "recommendation": info.get("recommendationKey", "N/A"),
        }
        
        # ─── Benchmark Comparison ─────────────────────────────
        benchmark = yf.Ticker(config.BENCHMARK_TICKER)
        bench_hist = benchmark.history(period=config.DEFAULT_PERIOD)
        
        if not bench_hist.empty:
            bench_year_ago = bench_hist['Close'].iloc[-252] if len(bench_hist) >= 252 else bench_hist['Close'].iloc[0]
            bench_current = bench_hist['Close'].iloc[-1]
            bench_1yr_return = round(((bench_current - bench_year_ago) / bench_year_ago) * 100, 2)
        else:
            bench_1yr_return = "N/A"
        
        return {
            "ticker": ticker,
            "company": company_data,
            "financials": financials,
            "performance": performance,
            "volatility_annualized_pct": volatility_annualized,
            "benchmark_1yr_return": bench_1yr_return,
            "price_history": hist,  # DataFrame for technical agent
            "status": "success"
        }
        
    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
            "status": "failed"
        }


def format_large_number(num) -> str:
    """Convert large numbers to readable format (1.2B, 3.4M etc)"""
    if num == "N/A" or num is None:
        return "N/A"
    try:
        num = float(num)
        if num >= 1_000_000_000_000:
            return f"${num/1_000_000_000_000:.1f}T"
        elif num >= 1_000_000_000:
            return f"${num/1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"${num/1_000_000:.1f}M"
        else:
            return f"${num:,.0f}"
    except:
        return str(num)