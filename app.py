import streamlit as st
import json
import os
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="FinSight — AI Stock Research",
    page_icon="📈",
    layout="wide"
)

st.title("📈 FinSight — Autonomous Financial Research Agent")
st.caption("Multi-agent AI system | Claude API + RAG over SEC filings + Technical Analysis")

with st.sidebar:
    st.header("🤖 How It Works")
    st.markdown("""
    **4 Specialized AI Agents:**
    
    🏦 **Agent 1 — Fundamentals**
    P/E, revenue, margins, FCF
    
    📰 **Agent 2 — Sentiment**
    Recent news analysis
    
    📊 **Agent 3 — Technical**
    RSI, MACD, Bollinger Bands
    
    📋 **Agent 4 — SEC RAG**
    10-K/10-Q filing analysis
    via ChromaDB vector store
    
    🧠 **Synthesis Agent**
    CIO-level recommendation
    """)
    st.divider()
    st.markdown("""
    **Tech Stack:**
    - Claude Sonnet (Anthropic)
    - ChromaDB + sentence-transformers
    - SEC EDGAR API
    - yfinance + TA-Lib
    """)
    st.divider()
    st.caption("⚠️ For research only. Not financial advice.")

ticker = st.text_input(
    "Enter Stock Ticker Symbol",
    placeholder="e.g. AAPL, NVDA, TSLA, MSFT, AMZN",
    max_chars=10
).upper().strip()

analyze = st.button("🔍 Run Analysis", type="primary")

if analyze and ticker:
    progress_bar = st.progress(0)
    status = st.status(f"Analyzing {ticker}...", expanded=True)

    with status:
        st.write("🏦 Running Financial Agent...")
        progress_bar.progress(10)

        try:
            from agents.orchestrator import run_orchestrator
            start = time.time()

            st.write("📰 Running Sentiment Agent...")
            progress_bar.progress(30)

            st.write("📊 Running Technical Agent...")
            progress_bar.progress(50)

            st.write("📋 Running SEC RAG Agent (fetching filings)...")
            progress_bar.progress(70)

            result = run_orchestrator(ticker)
            elapsed = round(time.time() - start, 1)

            st.write("🧠 Synthesizing final recommendation...")
            progress_bar.progress(90)

        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.stop()

    progress_bar.progress(100)
    status.update(label=f"✅ Analysis complete in {elapsed}s", state="complete")

    rec = result["recommendation"]
    signals = result["signals"]

    # Header metrics
    st.divider()
    rec_emoji = {"BUY": "🟢 BUY", "HOLD": "🟡 HOLD", "SELL": "🔴 SELL"}
    st.subheader(f"{rec_emoji.get(rec['recommendation'], rec['recommendation'])} — {result['company_name']} ({ticker})")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Price", f"${result['current_price']}")
    m2.metric("Recommendation", rec["recommendation"])
    m3.metric("Confidence", f"{int(float(rec['confidence_score'])*100)}%")
    m4.metric("Horizon", rec["investment_horizon"])
    m5.metric("Analysis Time", f"{elapsed}s")

    st.divider()

    # Agent signals
    st.subheader("🤖 Agent Signals")
    c1, c2, c3, c4 = st.columns(4)

    def fmt_signal(s):
        icons = {"BULLISH": "🟢 BULLISH", "BEARISH": "🔴 BEARISH", "NEUTRAL": "🟡 NEUTRAL"}
        return icons.get(s, s)

    c1.metric("🏦 Fundamental", fmt_signal(signals["financial"]))
    c2.metric("📰 Sentiment", fmt_signal(signals["sentiment"]))
    c3.metric("📊 Technical", fmt_signal(signals["technical"]))
    c4.metric("📋 SEC Filings", fmt_signal(signals["sec"]))

    st.divider()

    # Thesis and cases
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📝 Investment Thesis")
        st.info(rec["thesis"])

        st.subheader("🐂 Bull Case")
        st.success(rec["bull_case"])

        st.subheader("🐻 Bear Case")
        st.error(rec["bear_case"])

        st.subheader("📐 Position Sizing")
        st.warning(rec.get("position_sizing", "N/A"))

    with col_right:
        st.subheader("🚀 Key Catalysts")
        for cat in rec.get("key_catalysts", []):
            st.markdown(f"✅ {cat}")

        st.subheader("⚠️ Key Risks")
        for risk in rec.get("key_risks", []):
            st.markdown(f"❗ {risk}")

        st.subheader("🎯 Price Target")
        st.markdown(f"**{rec.get('price_target_upside', 'N/A')}**")

    st.divider()

    # Expandable agent details
    with st.expander("🏦 Fundamental Analysis Details"):
        fin = result["agent_results"]["financial"].get("analysis", {})
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Valuation:** {fin.get('valuation_assessment', 'N/A')}")
            st.markdown(f"**Health Score:** {fin.get('financial_health_score', 'N/A')}")
            st.markdown(f"**Growth Outlook:** {fin.get('growth_outlook', 'N/A')}")
        with col2:
            st.markdown("**Key Strengths:**")
            for s in fin.get("key_strengths", []):
                st.markdown(f"• {s}")
            st.markdown("**Key Concerns:**")
            for c in fin.get("key_concerns", []):
                st.markdown(f"• {c}")

    with st.expander("📰 Sentiment Analysis Details"):
        sent = result["agent_results"]["sentiment"].get("analysis", {})
        st.markdown(f"**News Summary:** {sent.get('news_summary', 'N/A')}")
        st.markdown(f"**Media Tone:** {sent.get('media_tone', 'N/A')}")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Positive Catalysts:**")
            for c in sent.get("positive_catalysts", []):
                st.markdown(f"✅ {c}")
        with col2:
            st.markdown("**Negative Risks:**")
            for r in sent.get("negative_risks", []):
                st.markdown(f"❗ {r}")

    with st.expander("📊 Technical Analysis Details"):
        tech = result["agent_results"]["technical"].get("analysis", {})
        indicators = result["agent_results"]["technical"].get("indicators", {})
        st.markdown(f"**Trend:** {tech.get('trend_assessment', 'N/A')}")
        st.markdown(f"**Momentum:** {tech.get('momentum_assessment', 'N/A')}")
        st.markdown(f"**Technical Summary:** {tech.get('technical_summary', 'N/A')}")
        if indicators:
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("RSI", indicators.get("rsi", "N/A"))
            t2.metric("MACD", indicators["macd"].get("macd", "N/A"))
            t3.metric("BB Position", f"{indicators['bollinger_bands'].get('position_pct', 'N/A')}%")
            t4.metric("Volume Ratio", f"{indicators['volume'].get('ratio', 'N/A')}x")

    with st.expander("📋 SEC Filing RAG Analysis"):
        rag = result["agent_results"]["rag"].get("analysis", {})
        st.markdown(f"**SEC Summary:** {rag.get('sec_summary', 'N/A')}")
        st.markdown(f"**Competitive Position:** {rag.get('competitive_position', 'N/A')}")
        st.markdown(f"**Management Tone:** {rag.get('management_tone', 'N/A')}")
        chunks = result["agent_results"]["rag"].get("chunks_indexed", 0)
        filings = result["agent_results"]["rag"].get("filings_analyzed", 0)
        st.caption(f"📊 Analyzed {filings} SEC filings | {chunks} chunks indexed in ChromaDB vector store")

    # Download button
    st.divider()
    report_path = f"output/reports/{ticker}_report.json"
    if os.path.exists(report_path):
        with open(report_path) as f:
            report_json = f.read()
        st.download_button(
            label="⬇️ Download Full JSON Report",
            data=report_json,
            file_name=f"{ticker}_finsight_report.json",
            mime="application/json",
            use_container_width=True
        )

elif analyze and not ticker:
    st.warning("⚠️ Please enter a stock ticker symbol first.")

else:
    st.markdown("""
    ### 🚀 How to use
    1. Enter any NYSE/NASDAQ stock ticker above (e.g. **AAPL**, **NVDA**, **TSLA**)
    2. Click **Run Analysis**
    3. Wait ~60 seconds while 4 AI agents analyze the stock
    4. Get a professional investment research brief
    
    ### 📊 What you get
    - **Fundamental analysis** — valuation, margins, growth, FCF
    - **Sentiment analysis** — news tone and catalysts  
    - **Technical analysis** — RSI, MACD, Bollinger Bands
    - **SEC filing insights** — risk factors, guidance, competition (via RAG)
    - **Final recommendation** — BUY/HOLD/SELL with confidence score and thesis
    """)