import { useState, useEffect, useRef, useCallback } from "react";
import Auth, { supabase } from "./Auth";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const TOOLTIPS = {
  "Current Price": "The latest traded price of this stock during market hours. Markets are open Monday–Friday 9:30 AM – 4:00 PM EST. Outside these hours, this reflects the most recent closing price.",
  "Signal": "FinSight's overall recommendation based on synthesizing all four AI agents: Fundamental, Sentiment, Technical, and SEC Filing analysis.",
  "Entry Price": "The price level at which FinSight suggests entering a position. For BUY signals this is the current price. For HOLD, it reflects your existing cost basis. For SELL, this is your exit point.",
  "Price Target": "The calculated dollar target price based on analyst consensus. Reaching this level would represent the expected upside or downside from the current price.",
  "52W High": "The highest price this stock has traded at over the past 52 weeks (one year). Acts as a key resistance level — price often struggles to break above this.",
  "52W Low": "The lowest price this stock has traded at over the past 52 weeks. Acts as a key support level — price often stabilizes or bounces near this level.",
  "Horizon": "The recommended time frame for holding this position. Short-term = days to weeks. Medium-term = 1–6 months. Long-term = 6+ months.",
  "Position Size": "How much of your portfolio FinSight suggests allocating. Small position = 1–3%. Medium = 3–7%. Large = 7–15%. Reflects risk level of the trade.",
  "Fundamental": "Based on valuation, profit margins, revenue growth, and balance sheet strength from live market data.",
  "Sentiment": "Based on recent news tone, analyst rating changes, and media coverage scored by Claude AI.",
  "Technical": "Based on RSI, MACD, Bollinger Bands, and moving average patterns from price history.",
  "SEC Filings": "Based on 10-K and 10-Q disclosures including risk factors and management guidance.",
  "RSI": "Relative Strength Index (0–100). Below 30 = oversold (potential buy signal). Above 70 = overbought (potential sell signal). Between 30–70 = neutral momentum.",
  "MACD": "Moving Average Convergence Divergence. When MACD line crosses above the signal line = bullish momentum. When it crosses below = bearish momentum.",
  "BB Position": "Where price sits within its Bollinger Band volatility range. Near 0% = price at lower band (oversold). Near 100% = price at upper band (overbought).",
  "Volume Ratio": "Current trading volume compared to the 20-day average. Above 1.5x signals unusually strong conviction behind today's price move.",
  "Confidence": "FinSight's conviction score — how strongly all four agents agree on the recommendation. Above 70% = strong signal. Below 50% = mixed signals, exercise caution.",
  "Health Score": "Overall financial health rated 1–10. Combines profitability, debt levels, revenue growth, and cash generation. Above 7 = financially strong company.",
};

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  :root{
    --bg:#06080f;--s1:#0b0e18;--s2:#0f1320;--s3:#141828;--s4:#1a2035;
    --b1:rgba(148,163,184,0.07);--b2:rgba(148,163,184,0.11);--b3:rgba(148,163,184,0.2);
    --blue:#3b82f6;--blue-l:#93c5fd;
    --txt:#e2e8f0;--txt2:#94a3b8;--txt3:#64748b;
    --green:#34d399;--gbg:rgba(52,211,153,0.06);--gb:rgba(52,211,153,0.18);
    --red:#f87171;--rbg:rgba(248,113,113,0.06);--rb:rgba(248,113,113,0.18);
    --amber:#fbbf24;--abg:rgba(251,191,36,0.06);--ab:rgba(251,191,36,0.18);
    --r:6px;--sans:'Inter',system-ui,sans-serif;--mono:'JetBrains Mono',monospace;
  }
  html{scroll-behavior:smooth}
  body{background:var(--bg);color:var(--txt);font-family:var(--sans);font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased;overflow-x:hidden}
  ::placeholder{color:var(--txt3)}
  ::-webkit-scrollbar{width:3px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--s4);border-radius:3px}

  /* Global tooltip portal */
  .g-tip{position:fixed;z-index:99999;pointer-events:none;background:#1e293b;border:1px solid rgba(148,163,184,0.25);border-radius:8px;padding:10px 14px;max-width:240px;font-size:12px;color:#e2e8f0;line-height:1.65;font-family:'Inter',sans-serif;font-weight:400;box-shadow:0 8px 32px rgba(0,0,0,0.7),0 0 0 1px rgba(148,163,184,0.1);backdrop-filter:blur(8px)}
  .g-tip-label{font-weight:600;color:#fff;margin-bottom:4px;font-size:12px}
  .tip-trigger{cursor:help;border-bottom:1px dashed rgba(148,163,184,0.35);display:inline}

  .nav{position:sticky;top:0;z-index:200;background:rgba(6,8,15,0.9);backdrop-filter:blur(16px);border-bottom:1px solid var(--b1);height:54px;display:flex;align-items:center;padding:0 32px;gap:12px}
  .logo{display:flex;align-items:center;gap:8px;margin-right:auto}
  .logo-icon{width:26px;height:26px;border-radius:6px;background:linear-gradient(135deg,#1e40af,#3b82f6);display:flex;align-items:center;justify-content:center}
  .logo-icon svg{width:13px;height:13px}
  .logo-name{font-size:14px;font-weight:600;color:var(--txt);letter-spacing:-0.02em}
  .tier{display:inline-flex;align-items:center;gap:5px;font-family:var(--mono);font-size:10px;font-weight:500;padding:3px 9px;border-radius:20px}
  .tier.alpha{background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.2);color:var(--blue-l)}
  .tier.free{background:var(--s2);border:1px solid var(--b1);color:var(--txt2)}
  .dot{width:5px;height:5px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  .nemail{font-family:var(--mono);font-size:10px;color:var(--txt3)}
  .n-btn-up{padding:5px 12px;border-radius:5px;background:var(--blue);border:none;color:#fff;font-size:11px;font-weight:500;cursor:pointer;font-family:var(--sans);transition:opacity .15s,transform .15s}
  .n-btn-up:hover{opacity:.85;transform:translateY(-1px)}
  .n-btn-out{padding:5px 12px;border-radius:5px;background:transparent;border:1px solid var(--b2);color:var(--txt2);font-size:11px;cursor:pointer;font-family:var(--sans);transition:color .15s,border-color .15s}
  .n-btn-out:hover{color:var(--txt);border-color:var(--b3)}

  .hero-outer{border-bottom:1px solid var(--b1);background:linear-gradient(180deg,var(--s1) 0%,var(--bg) 100%)}
  .hero{max-width:1120px;margin:0 auto;padding:64px 32px 48px;display:grid;grid-template-columns:1fr 420px;gap:48px;align-items:center}
  .h-tag{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:10px;color:var(--txt2);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:20px;padding:4px 10px;border-radius:20px;background:var(--s3);border:1px solid var(--b2)}
  .h-tag-d{width:4px;height:4px;border-radius:50%;background:var(--blue)}
  .h1{font-size:44px;font-weight:700;line-height:1.1;letter-spacing:-0.035em;color:var(--txt);margin-bottom:16px}
  .h1-muted{color:var(--txt3);font-weight:300}
  .h-sub{font-size:14px;line-height:1.75;color:var(--txt2);font-weight:400;max-width:420px;margin-bottom:28px}
  .h-search{display:flex;gap:8px}
  .h-inp{flex:1;padding:10px 14px;background:var(--s3);border:1px solid var(--b2);border-radius:var(--r);font-family:var(--mono);font-size:13px;font-weight:500;color:var(--txt);letter-spacing:0.04em;outline:none;transition:border-color .2s,box-shadow .2s,background .2s}
  .h-inp:focus{border-color:rgba(59,130,246,.4);background:var(--s4);box-shadow:0 0 0 3px rgba(59,130,246,.07)}
  .h-btn{padding:10px 22px;border-radius:var(--r);background:var(--blue);border:none;color:#fff;font-size:13px;font-weight:500;cursor:pointer;font-family:var(--sans);transition:opacity .15s,transform .15s,box-shadow .15s;box-shadow:0 2px 12px rgba(59,130,246,.25);white-space:nowrap}
  .h-btn:hover:not(:disabled){opacity:.88;transform:translateY(-1px);box-shadow:0 4px 20px rgba(59,130,246,.4)}
  .h-btn:disabled{background:var(--s3);color:var(--txt3);cursor:not-allowed;box-shadow:none}

  .autocomplete{position:absolute;top:calc(100% + 4px);left:0;right:0;background:#0f1320;border:1px solid rgba(148,163,184,0.15);border-radius:var(--r);overflow:hidden;z-index:300;box-shadow:0 12px 40px rgba(0,0,0,.7)}
  .ac-item{padding:10px 14px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;transition:background .15s}
  .ac-item:hover,.ac-item.active{background:var(--s3)}
  .ac-ticker{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--blue-l)}
  .ac-name{font-size:12px;color:var(--txt2)}

  .h-preview{background:var(--s2);border:1px solid var(--b2);border-radius:10px;padding:20px;transform:perspective(800px) rotateY(-4deg) rotateX(2deg);box-shadow:-8px 8px 40px rgba(0,0,0,.4)}
  .h-prev-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid var(--b1)}
  .h-prev-co{font-size:14px;font-weight:600;color:var(--txt);margin-bottom:3px}
  .h-prev-price{font-family:var(--mono);font-size:11px;color:var(--txt2)}
  .h-prev-rec{font-family:var(--mono);font-size:12px;font-weight:600;padding:4px 12px;border-radius:4px;letter-spacing:.06em;background:var(--gbg);border:1px solid var(--gb);color:var(--green)}
  .h-prev-row{display:flex;justify-content:space-between;font-size:11px;padding:5px 0;border-bottom:1px solid var(--b1)}
  .h-prev-row:last-child{border-bottom:none}
  .h-prev-k{color:var(--txt2)}
  .h-prev-v{color:var(--txt);font-family:var(--mono);font-size:11px}
  .h-prev-v.g{color:var(--green)}
  .h-prev-sigs{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--b1);border-radius:5px;overflow:hidden;margin-bottom:14px}
  .h-prev-sig{background:var(--s3);padding:7px 8px;text-align:center;font-family:var(--mono);font-size:9px;font-weight:600;letter-spacing:.05em}
  .h-prev-sig.b{color:var(--green)}
  .h-prev-sig.n{color:var(--txt2)}
  .h-prev-footer{font-size:10px;color:var(--txt2);line-height:1.6}

  .prog{display:flex;gap:3px;align-items:center;margin-top:12px}
  .ps{display:flex;align-items:center;gap:4px;font-family:var(--mono);font-size:10px;color:var(--txt3);transition:color .3s}
  .ps.on{color:var(--blue-l)}.ps.ok{color:var(--green)}
  .pd{width:4px;height:4px;border-radius:50%;background:currentColor;transition:transform .3s}
  .ps.on .pd{transform:scale(1.5)}
  .psep{color:var(--txt3);font-size:10px;margin:0 3px}

  .agents{max-width:1120px;margin:0 auto;display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--b1);border-top:1px solid var(--b1)}
  .ag{background:var(--bg);padding:22px;transition:background .18s}
  .ag:hover{background:var(--s1)}
  .ag-n{font-family:var(--mono);font-size:9px;color:var(--blue);font-weight:500;letter-spacing:.1em;margin-bottom:10px}
  .ag-t{font-size:13px;font-weight:500;color:var(--txt);margin-bottom:6px}
  .ag-d{font-size:12px;color:var(--txt2);line-height:1.6}

  .csrch{background:var(--s1);border-bottom:1px solid var(--b1);padding:12px 32px;display:flex;gap:8px;align-items:center;position:relative;z-index:50}
  .c-inp{width:240px;padding:9px 13px;background:var(--s2);border:1px solid var(--b2);border-radius:var(--r);font-family:var(--mono);font-size:12px;font-weight:500;color:var(--txt);outline:none;transition:border-color .2s}
  .c-inp:focus{border-color:rgba(59,130,246,.35)}
  .c-btn{padding:9px 20px;border-radius:var(--r);background:var(--blue);border:none;color:#fff;font-size:12px;font-weight:500;cursor:pointer;font-family:var(--sans);transition:opacity .15s}
  .c-btn:hover:not(:disabled){opacity:.85}
  .c-btn:disabled{background:var(--s3);color:var(--txt3);cursor:not-allowed}
  .pdf-btn{display:flex;align-items:center;gap:6px;padding:8px 16px;border-radius:var(--r);background:transparent;border:1px solid var(--b2);color:var(--txt2);font-size:12px;font-weight:500;cursor:pointer;font-family:var(--sans);transition:all .15s;margin-left:auto}
  .pdf-btn:hover{border-color:var(--blue);color:var(--blue-l)}

  .wrap{max-width:1120px;margin:0 auto;padding:24px 32px}

  .rh{background:var(--s2);border:1px solid var(--b2);border-radius:var(--r);padding:24px 28px;display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;position:relative;overflow:hidden}
  .rh::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(59,130,246,.5),transparent)}
  .rh-co{font-size:22px;font-weight:600;color:var(--txt);margin-bottom:5px;letter-spacing:-.02em}
  .rh-m{font-family:var(--mono);font-size:11px;color:var(--txt2);display:flex;gap:14px;flex-wrap:wrap}
  .rh-r{display:flex;flex-direction:column;align-items:flex-end;gap:8px}
  .conf-l{font-family:var(--mono);font-size:9px;color:var(--txt3);letter-spacing:.1em;text-transform:uppercase;margin-bottom:2px}
  .conf-v{font-family:var(--mono);font-size:32px;font-weight:600;color:var(--blue-l);line-height:1}
  .rec-c{font-family:var(--mono);font-size:15px;font-weight:600;padding:7px 22px;border-radius:var(--r);letter-spacing:.08em}
  .rec-c.BUY{background:var(--gbg);border:1px solid var(--gb);color:var(--green)}
  .rec-c.SELL{background:var(--rbg);border:1px solid var(--rb);color:var(--red)}
  .rec-c.HOLD{background:var(--abg);border:1px solid var(--ab);color:var(--amber)}

  /* Price action banner */
  .price-banner{background:var(--s2);border:1px solid var(--b2);border-radius:var(--r);padding:0;margin-bottom:12px;display:grid;grid-template-columns:repeat(6,1fr);overflow:hidden}
  .pb-cell{padding:16px 20px;border-right:1px solid var(--b1)}
  .pb-cell:last-child{border-right:none}
  .pb-label{font-size:10px;color:var(--txt3);font-family:var(--mono);letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px}
  .pb-val{font-family:var(--mono);font-size:20px;font-weight:600;color:var(--txt)}
  .pb-val.g{color:var(--green)}
  .pb-val.r{color:var(--red)}
  .pb-val.a{color:var(--amber)}
  .pb-sub{font-size:10px;color:var(--txt3);margin-top:3px;font-family:var(--mono)}

  /* Buy/Sell target box */
  .action-box{border-radius:var(--r);padding:20px 24px;margin-bottom:12px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .action-box.buy{background:rgba(52,211,153,0.05);border:1px solid rgba(52,211,153,0.2)}
  .action-box.sell{background:rgba(248,113,113,0.05);border:1px solid rgba(248,113,113,0.2)}
  .action-box.hold{background:rgba(251,191,36,0.05);border:1px solid rgba(251,191,36,0.2)}
  .ab-title{font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;font-family:var(--mono);margin-bottom:12px}
  .ab-title.g{color:var(--green)}.ab-title.r{color:var(--red)}.ab-title.a{color:var(--amber)}
  .ab-row{display:flex;justify-content:space-between;align-items:baseline;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.05)}
  .ab-row:last-child{border-bottom:none}
  .ab-k{font-size:11px;color:var(--txt3)}
  .ab-v{font-family:var(--mono);font-size:13px;font-weight:600;color:var(--txt)}
  .ab-v.g{color:var(--green)}.ab-v.r{color:var(--red)}.ab-v.a{color:var(--amber)}

  /* Chart */
  .chart-wrap{background:var(--s1);border:1px solid var(--b1);border-radius:var(--r);margin-bottom:12px;overflow:hidden}
  .chart-head{padding:12px 16px;border-bottom:1px solid var(--b1);display:flex;justify-content:space-between;align-items:center}
  .chart-tabs{display:flex;gap:2px}
  .chart-tab{padding:4px 10px;border-radius:4px;font-family:var(--mono);font-size:10px;font-weight:500;color:var(--txt2);cursor:pointer;border:none;background:transparent;transition:all .15s}
  .chart-tab.active{background:var(--blue);color:white}
  .chart-tab:hover:not(.active){background:var(--s3);color:var(--txt)}
  .chart-change{font-family:var(--mono);font-size:12px;font-weight:600}
  .chart-change.pos{color:var(--green)}.chart-change.neg{color:var(--red)}
  .chart-body{padding:16px;position:relative}
  .chart-hover-info{font-family:var(--mono);font-size:11px;color:var(--txt);height:18px;margin-bottom:4px;display:flex;gap:16px}
  .chart-loading{padding:40px;text-align:center;color:var(--txt3);font-size:12px;font-family:var(--mono)}

  .sigs{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--b1);border:1px solid var(--b1);border-radius:var(--r);overflow:hidden;margin-bottom:12px}
  .sc{background:var(--s1);padding:11px 16px;display:flex;justify-content:space-between;align-items:center}
  .sl{font-size:11px;color:var(--txt2)}
  .sp{font-family:var(--mono);font-size:9px;font-weight:600;padding:2px 8px;border-radius:20px;letter-spacing:.07em}
  .sp.BULLISH{background:var(--gbg);border:1px solid var(--gb);color:var(--green)}
  .sp.BEARISH{background:var(--rbg);border:1px solid var(--rb);color:var(--red)}
  .sp.NEUTRAL{background:var(--s3);border:1px solid var(--b1);color:var(--txt3)}

  .g2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
  .g2a{display:grid;grid-template-columns:1fr 260px;gap:12px;margin-bottom:12px}
  .pnl{background:var(--s1);border:1px solid var(--b1);border-radius:var(--r);overflow:hidden}
  .ph{padding:10px 16px;border-bottom:1px solid var(--b1);display:flex;justify-content:space-between;align-items:center}
  .pt{font-family:var(--mono);font-size:10px;font-weight:600;color:var(--txt2);letter-spacing:.08em;text-transform:uppercase}
  .pb{padding:16px}
  .prose{font-size:13px;line-height:1.8;color:var(--txt2)}
  .bg{width:2px;background:var(--green);opacity:.5;border-radius:2px;flex-shrink:0}
  .br{width:2px;background:var(--red);opacity:.5;border-radius:2px;flex-shrink:0}
  .kv{display:flex;justify-content:space-between;align-items:baseline;padding:7px 0;border-bottom:1px solid var(--b1);gap:8px}
  .kv:last-child{border-bottom:none}
  .kk{font-size:11px;color:var(--txt3)}
  .kv-v{font-size:11px;font-weight:500;color:var(--txt);text-align:right}
  .kv-v.g{color:var(--green)}.kv-v.b{color:var(--blue-l)}
  .li{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--b1)}
  .li:last-child{border-bottom:none}
  .li-i{width:16px;height:16px;border-radius:50%;flex-shrink:0;margin-top:2px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700}
  .li-i.p{background:var(--gbg);border:1px solid var(--gb);color:var(--green)}
  .li-i.n{background:var(--rbg);border:1px solid var(--rb);color:var(--red)}
  .li-t{font-size:13px;color:var(--txt2);line-height:1.65}
  .tg{display:grid;grid-template-columns:repeat(4,1fr)}
  .tc{padding:14px 16px;border-right:1px solid var(--b1)}
  .tc:last-child{border-right:none}
  .tl{font-size:11px;color:var(--txt2);margin-bottom:6px}
  .tv{font-family:var(--mono);font-size:20px;font-weight:500;margin-bottom:3px}
  .ts{font-family:var(--mono);font-size:10px;color:var(--txt3)}
  .err{background:var(--rbg);border:1px solid var(--rb);border-radius:var(--r);padding:10px 14px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center}
  .err-t{font-size:13px;color:var(--red)}
  .foot{text-align:center;padding:18px 0;font-size:11px;color:var(--txt3);letter-spacing:.03em;border-top:1px solid var(--b1);margin-top:4px}

  @media print{
    body{background:white;color:#111}
    .nav,.csrch,.chart-wrap,.pdf-btn,.action-box,.foot{display:none!important}
    .wrap{padding:0;max-width:100%}
    .rh,.pnl,.sigs,.price-banner{background:white;border:1px solid #ddd;break-inside:avoid;margin-bottom:8px}
    .pt{color:#374151!important}.prose,.li-t,.kv-v,.tb-val{color:#111!important}
    .rec-c.BUY{background:#d1fae5;border-color:#6ee7b7;color:#065f46}
    .rec-c.HOLD{background:#fef3c7;border-color:#fcd34d;color:#92400e}
    .rec-c.SELL{background:#fee2e2;border-color:#fca5a5;color:#991b1b}
  }
`;

// Global tooltip rendered via fixed position
function Tip({ label, children }) {
  const [pos, setPos] = useState(null);
  const def = TOOLTIPS[label];
  if (!def) return <span>{children || label}</span>;

  return (
    <>
      <span
        className="tip-trigger"
        onMouseMove={(e) => setPos({ x: e.clientX, y: e.clientY })}
        onMouseLeave={() => setPos(null)}
      >
        {children || label}
      </span>
      {pos && typeof document !== 'undefined' && (() => {
        const el = document.getElementById('tip-root');
        if (!el) return null;
        const left = Math.min(pos.x + 12, window.innerWidth - 260);
        const top = pos.y - 8;
        return (
          <div
            className="g-tip"
            style={{ left, top: top - 80, transform: 'translateY(-100%)' }}
            id="tip-render"
          >
            <div className="g-tip-label">{label}</div>
            {def}
          </div>
        );
      })()}
    </>
  );
}

// Interactive SVG chart with crosshair
function PriceChart({ ticker }) {
  const [period, setPeriod] = useState("1M");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hover, setHover] = useState(null);
  const svgRef = useRef(null);
  const periods = ["1D", "1W", "1M", "3M", "6M", "1Y", "5Y", "MAX"];

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setHover(null);
    fetch(`${API_URL}/chart/${ticker}?period=${period}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [ticker, period]);

  const W = 800, H = 120, padX = 4, padY = 8;

  const getChartCoords = useCallback((prices) => {
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;
    return { min, max, range,
      toX: (i) => padX + (i / (prices.length - 1)) * (W - padX * 2),
      toY: (p) => H - padY - ((p - min) / range) * (H - padY * 2)
    };
  }, []);

  const handleMouseMove = (e) => {
    if (!data?.data?.length || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * W;
    const prices = data.data.map(d => d.close);
    const { toX, toY } = getChartCoords(prices);
    let closest = 0;
    let minDist = Infinity;
    prices.forEach((_, i) => {
      const dist = Math.abs(toX(i) - mx);
      if (dist < minDist) { minDist = dist; closest = i; }
    });
    const point = data.data[closest];
    const d = new Date(point.date);
    let label;
    if (period === "1D") {
      label = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true });
    } else if (period === "1W") {
      label = d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }) + " · " + d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
    } else if (period === "5Y" || period === "MAX") {
      label = d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
    } else {
      label = d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    }
    setHover({ idx: closest, price: point.close, date: label, x: toX(closest), y: toY(point.close) });
  };

  const renderChart = () => {
    if (!data?.data?.length) return null;
    const prices = data.data.map(d => d.close);
    const { min, max, range, toX, toY } = getChartCoords(prices);
    const pts = prices.map((p, i) => `${toX(i)},${toY(p)}`);
    const areaPath = `M${pts[0]} L${pts.join(" L")} L${toX(prices.length-1)},${H} L${toX(0)},${H} Z`;
    const color = data.is_positive ? "#34d399" : "#f87171";

    return (
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", height: "100px", cursor: "crosshair", display: "block" }}
        preserveAspectRatio="none"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.15" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#cg)" />
        <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
        {hover && (
          <>
            <line x1={hover.x} y1={padY} x2={hover.x} y2={H - padY} stroke="rgba(255,255,255,0.2)" strokeWidth="1" strokeDasharray="3,3" />
            <circle cx={hover.x} cy={hover.y} r="4" fill={color} stroke="#06080f" strokeWidth="2" />
          </>
        )}
      </svg>
    );
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    if (period === "1D") return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true });
    if (period === "1W") return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }) + " " + d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
    if (period === "MAX" || period === "5Y") return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  return (
    <div className="chart-wrap">
      <div className="chart-head">
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span className="pt" style={{ color: "var(--txt2)" }}>Price History</span>
          {data && <span className={`chart-change ${data.is_positive ? "pos" : "neg"}`}>{data.is_positive ? "+" : ""}{data.change_pct}%</span>}
        </div>
        <div className="chart-tabs">
          {periods.map(p => <button key={p} className={`chart-tab ${period === p ? "active" : ""}`} onClick={() => setPeriod(p)}>{p}</button>)}
        </div>
      </div>
      <div className="chart-body">
        {/* Hover price display */}
        <div className="chart-hover-info">
          {hover ? (
            <>
              <span style={{ color: "var(--txt)", fontWeight: 600, fontFamily: "var(--mono)" }}>${hover.price.toFixed(2)}</span>
              <span style={{ color: "var(--txt2)" }}>{hover.date}</span>
              {period === "1D" && <span style={{ color: "var(--txt3)", fontSize: "10px" }}>· move cursor to track price by time</span>}
            </>
          ) : (
            <span style={{ color: "var(--txt3)" }}>
              {period === "1D" ? "Hover over chart to see price at each minute" : "Hover over chart to see historical price"}
            </span>
          )}
        </div>
        {loading ? <div className="chart-loading">Loading chart…</div> : data?.data?.length ? (
          <>
            {renderChart()}
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px" }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "var(--txt3)" }}>
                {formatDate(data.data[0]?.date)} · ${Math.min(...data.data.map(d => d.close)).toFixed(2)}
              </span>
              <span style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "var(--txt3)" }}>
                ${Math.max(...data.data.map(d => d.close)).toFixed(2)} · {formatDate(data.data[data.data.length-1]?.date)}
              </span>
            </div>
          </>
        ) : <div className="chart-loading">No data available</div>}
      </div>
    </div>
  );
}

function SearchInput({ value, onChange, onSelect, onSubmit, placeholder, className, style }) {
  const [suggestions, setSuggestions] = useState([]);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [showSugg, setShowSugg] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (value.length < 1) { setSuggestions([]); return; }
    fetch(`${API_URL}/search?q=${encodeURIComponent(value)}`).then(r => r.json()).then(d => { setSuggestions(d); setShowSugg(true); setActiveIdx(-1); }).catch(() => setSuggestions([]));
  }, [value]);

  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setShowSugg(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const handleKey = (e) => {
    if (e.key === "ArrowDown") setActiveIdx(i => Math.min(i+1, suggestions.length-1));
    else if (e.key === "ArrowUp") setActiveIdx(i => Math.max(i-1, -1));
    else if (e.key === "Enter") {
      if (activeIdx >= 0 && suggestions[activeIdx]) { onSelect(suggestions[activeIdx].ticker); setSuggestions([]); setShowSugg(false); }
      else { onSubmit(); setShowSugg(false); }
    } else if (e.key === "Escape") setShowSugg(false);
  };

  return (
    <div ref={ref} style={{ position: "relative", flex: style?.width ? undefined : 1 }}>
      <input className={className} style={style} value={value}
        onChange={e => { onChange(e.target.value.toUpperCase()); setShowSugg(true); }}
        onKeyDown={handleKey} onFocus={() => suggestions.length && setShowSugg(true)}
        placeholder={placeholder} autoComplete="off" />
      {showSugg && suggestions.length > 0 && (
        <div className="autocomplete">
          {suggestions.map((s, i) => (
            <div key={s.ticker} className={`ac-item ${i === activeIdx ? "active" : ""}`}
              onMouseDown={() => { onSelect(s.ticker); setSuggestions([]); setShowSugg(false); }}>
              <div style={{display:"flex",alignItems:"center",gap:"7px"}}>
                <span className="ac-ticker">{s.ticker}</span>
                {s.exchange && <span style={{fontFamily:"var(--mono)",fontSize:"9px",color:"var(--txt3)",background:"var(--s3)",padding:"1px 5px",borderRadius:"3px"}}>{s.exchange}</span>}
              </div>
              <span className="ac-name">{s.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Global tooltip container component
function TipPortal() {
  return <div id="tip-root" style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 99999 }} />;
}

export default function App() {
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [si, setSi] = useState(0);
  const [session, setSession] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [tipState, setTipState] = useState(null);

  const stages = ["Fundamentals", "Sentiment", "Technicals", "SEC Filings", "Synthesis"];

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session); setAuthLoading(false);
      if (session) fp(session.access_token);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, s) => {
      setSession(s); if (s) fp(s.access_token);
    });
    return () => subscription.unsubscribe();
  }, []);

  const fp = async (t) => {
    try { const r = await fetch(`${API_URL}/me`, { headers: { Authorization: `Bearer ${t}` } }); setProfile(await r.json()); } catch {}
  };

  const upgrade = async () => {
    try { const r = await fetch(`${API_URL}/create-checkout`, { method: "POST", headers: { Authorization: `Bearer ${session.access_token}` } }); const d = await r.json(); window.location.href = d.checkout_url; } catch {}
  };

  const analyze = async (t) => {
    const tick = (t || ticker).trim().toUpperCase();
    if (!tick) return;
    if (t) setTicker(t);
    setLoading(true); setResult(null); setError(null); setSi(0);
    let i = 0;
    const iv = setInterval(() => { i = Math.min(i+1, stages.length-1); setSi(i); }, 11000);
    try {
      const r = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ ticker: tick }),
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail?.message || e.detail || r.statusText); }
      setResult(await r.json()); fp(session.access_token);
    } catch (e) { setError(e.message); }
    finally { clearInterval(iv); setLoading(false); }
  };

  if (authLoading) return <><style>{css}</style><div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}><span style={{ color: "var(--txt3)", fontSize: "12px" }}>Loading…</span></div></>;
  if (!session) return <><style>{css}</style><Auth onAuth={setSession} /></>;

  const rec = result?.recommendation;
  const sigs = result?.signals;
  const ti = result?.agent_results?.technical?.indicators;
  const rag = result?.agent_results?.rag?.analysis;
  const fin = result?.agent_results?.financial?.analysis;
  const isAlpha = profile?.tier === "alpha";
  const currentPrice = result?.current_price;

  // Calculate buy/sell prices from upside string e.g. "+11% upside from current price"
  const calcTargetPrice = () => {
    if (!rec?.price_target_upside || !currentPrice) return null;
    const match = rec.price_target_upside.match(/([+-]?\d+(\.\d+)?)\s*%/);
    if (!match) return null;
    const pct = parseFloat(match[1]);
    return (currentPrice * (1 + pct / 100)).toFixed(2);
  };
  const targetPrice = calcTargetPrice();

  // Action box color
  const actionClass = rec?.recommendation === "BUY" ? "buy" : rec?.recommendation === "SELL" ? "sell" : "hold";
  const actionColor = rec?.recommendation === "BUY" ? "g" : rec?.recommendation === "SELL" ? "r" : "a";

  return (
    <>
      <style>{css}</style>

      {/* Global tooltip that renders on top of everything */}
      {tipState && (
        <div className="g-tip" style={{ left: Math.min(tipState.x + 16, window.innerWidth - 260), top: tipState.y - 90, position: "fixed", zIndex: 99999, pointerEvents: "none" }}>
          <div className="g-tip-label">{tipState.label}</div>
          {tipState.def}
        </div>
      )}

      <nav className="nav">
        <div className="logo">
          <div className="logo-icon">
            <svg viewBox="0 0 13 13" fill="none"><polyline points="1,10 4.5,5.5 7.5,7.5 12,2" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </div>
          <span className="logo-name">FinSight</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {profile && <div className={`tier ${isAlpha ? "alpha" : "free"}`}>{isAlpha ? <><div className="dot" />Alpha</> : `${profile.analyses_today}/${profile.daily_limit} today`}</div>}
          <span className="nemail">{session.user.email}</span>
          {!isAlpha && <button className="n-btn-up" onClick={upgrade}>Upgrade</button>}
          <button className="n-btn-out" onClick={() => supabase.auth.signOut()}>Sign out</button>
        </div>
      </nav>

      {!result && !loading && (
        <div className="hero-outer">
          <div className="hero">
            <div>
              <div className="h-tag"><div className="h-tag-d" />AI Research Terminal</div>
              <h1 className="h1">Know more<br />before you invest.<br /><span className="h1-muted">Without the hours of research.</span></h1>
              <p className="h-sub">Four specialized AI agents analyze any publicly traded stock — fundamentals, news sentiment, SEC filings, and technicals — and synthesize a complete investment brief.</p>
              <div className="h-search">
                <SearchInput className="h-inp" value={ticker} onChange={setTicker} onSelect={(t) => { setTicker(t); analyze(t); }} onSubmit={() => analyze()} placeholder="Search by name or ticker — Apple, NVDA, Tesla..." />
                <button className="h-btn" onClick={() => analyze()} disabled={!ticker.trim()}>Analyze</button>
              </div>
            </div>
            <div>
              <div className="h-preview">
                <div className="h-prev-top">
                  <div><div className="h-prev-co">Apple Inc.</div><div className="h-prev-price">AAPL · $264.18</div></div>
                  <div className="h-prev-rec">BUY</div>
                </div>
                <div className="h-prev-sigs">{["BULLISH","BULLISH","NEUTRAL","NEUTRAL"].map((s,i) => <div key={i} className={`h-prev-sig ${s==="BULLISH"?"b":"n"}`}>{s}</div>)}</div>
                {[{k:"Confidence",v:"72%",c:""},{k:"Price Target",v:"+11% upside",c:"g"},{k:"Entry Price",v:"$264.18",c:""},{k:"Target Price",v:"$293.24",c:"g"}].map(({k,v,c}) => (
                  <div key={k} className="h-prev-row"><span className="h-prev-k">{k}</span><span className={`h-prev-v ${c}`}>{v}</span></div>
                ))}
                <div style={{height:"8px"}}/>
                <div className="h-prev-footer">Apple demonstrates exceptional operational excellence with industry-leading margins...</div>
              </div>
            </div>
          </div>
          <div className="agents">
            {[
              {n:"01",t:"Fundamental Analysis",d:"P/E, revenue growth, margins, FCF, ROE from live market data"},
              {n:"02",t:"Sentiment Analysis",d:"Real-time news, analyst ratings, media sentiment via Claude"},
              {n:"03",t:"Technical Analysis",d:"RSI, MACD, Bollinger Bands, moving averages, volume profile"},
              {n:"04",t:"SEC Filing Analysis",d:"10-K/10-Q risk factors, guidance, competition via vector search"},
            ].map(({n,t,d}) => <div key={n} className="ag"><div className="ag-n">{n}</div><div className="ag-t">{t}</div><div className="ag-d">{d}</div></div>)}
          </div>
        </div>
      )}

      {(result || loading) && (
        <div className="csrch">
          <SearchInput className="c-inp" value={ticker} onChange={setTicker} onSelect={(t) => { setTicker(t); analyze(t); }} onSubmit={() => analyze()} placeholder="Search ticker or company..." style={{ width: "280px" }} />
          <button className="c-btn" onClick={() => analyze()} disabled={loading || !ticker.trim()}>{loading ? "Analyzing…" : "Analyze"}</button>
          {loading && (
            <div className="prog">
              {stages.map((s,i) => (
                <span key={i} style={{display:"flex",alignItems:"center"}}>
                  <span className={`ps ${i===si?"on":i<si?"ok":""}`}><span className="pd"/>{s}</span>
                  {i<stages.length-1&&<span className="psep">·</span>}
                </span>
              ))}
            </div>
          )}
          {result && rec && (
            <button className="pdf-btn" onClick={() => window.print()}>
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M2 9v2h9V9M6.5 1v7M4 6l2.5 2.5L9 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
              Download Report
            </button>
          )}
        </div>
      )}

      <div className="wrap">
        {error && <div className="err"><span className="err-t">{error}</span>{error.includes("Daily limit")&&<button className="n-btn-up" onClick={upgrade}>Upgrade to Alpha</button>}</div>}

        {result && rec && (
          <>
            <div className="rh">
              <div>
                <div className="rh-co">{result.company_name}</div>
                <div className="rh-m">
                  <span>{result.ticker}</span>
                  <span>Current price: <strong style={{color:"var(--txt)"}}>${result.current_price}</strong></span>
                  <span>{rec.investment_horizon}</span>
                  <span style={{color:"var(--txt3)"}}>Analysis took {result.elapsed_seconds}s</span>
                </div>
              </div>
              <div className="rh-r">
                <div>
                  <div className="conf-l"
                    onMouseMove={(e) => setTipState({ label: "Confidence", def: TOOLTIPS["Confidence"], x: e.clientX, y: e.clientY })}
                    onMouseLeave={() => setTipState(null)}
                    style={{ cursor: "help", borderBottom: "1px dashed rgba(148,163,184,0.3)", display: "inline-block" }}>
                    Confidence
                  </div>
                  <div className="conf-v">{Math.round(rec.confidence_score*100)}%</div>
                </div>
                <div className={`rec-c ${rec.recommendation}`}>{rec.recommendation}</div>
              </div>
            </div>

            {/* Price banner with buy/sell price */}
            <div className="price-banner">
              <div className="pb-cell">
                <div className="pb-label" onMouseMove={(e) => setTipState({ label: "Current Price", def: TOOLTIPS["Current Price"], x: e.clientX, y: e.clientY })} onMouseLeave={() => setTipState(null)} style={{cursor:"help",borderBottom:"1px dashed rgba(148,163,184,0.3)",display:"inline-block"}}>Current Price</div>
                <div className="pb-val">${currentPrice}</div>
                <div className="pb-sub">Live market</div>
              </div>
              <div className="pb-cell">
                <div className="pb-label" onMouseMove={(e) => setTipState({ label: "Signal", def: TOOLTIPS["Signal"], x: e.clientX, y: e.clientY })} onMouseLeave={() => setTipState(null)} style={{cursor:"help",borderBottom:"1px dashed rgba(148,163,184,0.3)",display:"inline-block"}}>Signal</div>
                <div className={`pb-val ${actionColor}`}>{rec.recommendation}</div>
                <div className="pb-sub">{Math.round(rec.confidence_score*100)}% confidence</div>
              </div>
              <div className="pb-cell">
                <div className="pb-label" onMouseMove={(e) => setTipState({ label: "Entry Price", def: TOOLTIPS["Entry Price"], x: e.clientX, y: e.clientY })} onMouseLeave={() => setTipState(null)} style={{cursor:"help",borderBottom:"1px dashed rgba(148,163,184,0.3)",display:"inline-block"}}>{rec.recommendation === "SELL" ? "Exit Price" : "Entry Price"}</div>
                <div className={`pb-val ${actionColor}`}>${currentPrice}</div>
                <div className="pb-sub">Current level</div>
              </div>
              <div className="pb-cell">
                <div className="pb-label" onMouseMove={(e) => setTipState({ label: "Price Target", def: TOOLTIPS["Price Target"], x: e.clientX, y: e.clientY })} onMouseLeave={() => setTipState(null)} style={{cursor:"help",borderBottom:"1px dashed rgba(148,163,184,0.3)",display:"inline-block"}}>Price Target</div>
                <div className="pb-val g">{targetPrice ? `$${targetPrice}` : rec.price_target_upside}</div>
                <div className="pb-sub">{rec.price_target_upside}</div>
              </div>
              <div className="pb-cell">
                <div className="pb-label" onMouseMove={(e) => setTipState({ label: "52W High", def: TOOLTIPS["52W High"], x: e.clientX, y: e.clientY })} onMouseLeave={() => setTipState(null)} style={{cursor:"help",borderBottom:"1px dashed rgba(148,163,184,0.3)",display:"inline-block"}}>52W High</div>
                <div className="pb-val">{result.agent_results?.financial?.raw_data?.financials?.["52_week_high"] ? `$${result.agent_results.financial.raw_data.financials["52_week_high"]}` : "—"}</div>
                <div className="pb-sub">Resistance</div>
              </div>
              <div className="pb-cell">
                <div className="pb-label" onMouseMove={(e) => setTipState({ label: "52W Low", def: TOOLTIPS["52W Low"], x: e.clientX, y: e.clientY })} onMouseLeave={() => setTipState(null)} style={{cursor:"help",borderBottom:"1px dashed rgba(148,163,184,0.3)",display:"inline-block"}}>52W Low</div>
                <div className="pb-val">{result.agent_results?.financial?.raw_data?.financials?.["52_week_low"] ? `$${result.agent_results.financial.raw_data.financials["52_week_low"]}` : "—"}</div>
                <div className="pb-sub">Support</div>
              </div>
            </div>

            {/* Chart */}
            <PriceChart ticker={result.ticker} />

            {/* Signals with working tooltips */}
            <div className="sigs">
              {[{l:"Fundamental",s:sigs.financial},{l:"Sentiment",s:sigs.sentiment},{l:"Technical",s:sigs.technical},{l:"SEC Filings",s:sigs.sec}].map(({l,s}) => (
                <div key={l} className="sc">
                  <span className="sl"
                    onMouseMove={(e) => setTipState({ label: l, def: TOOLTIPS[l], x: e.clientX, y: e.clientY })}
                    onMouseLeave={() => setTipState(null)}
                    style={{ cursor: "help", borderBottom: "1px dashed rgba(148,163,184,0.3)" }}>
                    {l}
                  </span>
                  <span className={`sp ${s}`}>{s}</span>
                </div>
              ))}
            </div>

            <div className="g2a">
              <div className="pnl">
                <div className="ph"><span className="pt">Investment Thesis</span></div>
                <div className="pb"><p className="prose">{rec.thesis}</p></div>
              </div>
              <div className="pnl">
                <div className="ph"><span className="pt">Key Metrics</span></div>
                <div className="pb">
                  <div className="kv">
                    <span className="kk"
                      onMouseMove={(e) => setTipState({ label: "Price Target", def: TOOLTIPS["Price Target"], x: e.clientX, y: e.clientY })}
                      onMouseLeave={() => setTipState(null)}
                      style={{ cursor: "help", borderBottom: "1px dashed rgba(100,116,139,0.4)" }}>Price Target</span>
                    <span className="kv-v g">{rec.price_target_upside}</span>
                  </div>
                  <div className="kv"><span className="kk" onMouseMove={(e) => setTipState({ label: "Horizon", def: TOOLTIPS["Horizon"], x: e.clientX, y: e.clientY })} onMouseLeave={() => setTipState(null)} style={{cursor:"help",borderBottom:"1px dashed rgba(100,116,139,0.4)"}}>Horizon</span><span className="kv-v">{rec.investment_horizon}</span></div>
                  {fin && <>
                    <div className="kv">
                      <span className="kk"
                        onMouseMove={(e) => setTipState({ label: "Health Score", def: TOOLTIPS["Health Score"], x: e.clientX, y: e.clientY })}
                        onMouseLeave={() => setTipState(null)}
                        style={{ cursor: "help", borderBottom: "1px dashed rgba(100,116,139,0.4)" }}>Health Score</span>
                      <span className="kv-v b">{fin.financial_health_score?.split("/")[0]?.split(" ")[0]}/10</span>
                    </div>
                    <div className="kv"><span className="kk" onMouseMove={(e) => setTipState({ label: "Position Size", def: TOOLTIPS["Position Size"], x: e.clientX, y: e.clientY })} onMouseLeave={() => setTipState(null)} style={{cursor:"help",borderBottom:"1px dashed rgba(100,116,139,0.4)"}}>Position Size</span><span className="kv-v">{rec.position_sizing?.split(" ").slice(0,2).join(" ")}</span></div>
                  </>}
                </div>
              </div>
            </div>

            <div className="g2">
              <div className="pnl">
                <div className="ph"><span className="pt">Bull Case</span></div>
                <div className="pb" style={{display:"flex",gap:"12px"}}><div className="bg"/><p className="prose">{rec.bull_case}</p></div>
              </div>
              <div className="pnl">
                <div className="ph"><span className="pt">Bear Case</span></div>
                <div className="pb" style={{display:"flex",gap:"12px"}}><div className="br"/><p className="prose">{rec.bear_case}</p></div>
              </div>
            </div>

            <div className="g2">
              <div className="pnl">
                <div className="ph"><span className="pt">Key Catalysts</span></div>
                <div className="pb">{rec.key_catalysts?.map((c,i) => <div key={i} className="li"><div className="li-i p">+</div><span className="li-t">{c}</span></div>)}</div>
              </div>
              <div className="pnl">
                <div className="ph"><span className="pt">Key Risks</span></div>
                <div className="pb">{rec.key_risks?.map((r,i) => <div key={i} className="li"><div className="li-i n">−</div><span className="li-t">{r}</span></div>)}</div>
              </div>
            </div>

            {ti && (
              <div className="pnl" style={{marginBottom:"12px"}}>
                <div className="ph"><span className="pt">Technical Indicators</span></div>
                <div className="tg">
                  {[
                    {l:"RSI",v:ti.rsi,c:ti.rsi<30?"var(--green)":ti.rsi>70?"var(--red)":"var(--txt)",s:ti.rsi<30?"Oversold":ti.rsi>70?"Overbought":"Neutral"},
                    {l:"MACD",v:ti.macd?.macd,c:ti.macd?.histogram>0?"var(--green)":"var(--red)",s:`Signal ${ti.macd?.signal}`},
                    {l:"BB Position",v:`${ti.bollinger_bands?.position_pct}%`,c:"var(--txt)",s:"0=lower band"},
                    {l:"Volume Ratio",v:`${ti.volume?.ratio}×`,c:ti.volume?.ratio>1.5?"var(--blue-l)":"var(--txt)",s:"vs 20-day avg"},
                  ].map(({l,v,c,s}) => (
                    <div key={l} className="tc">
                      <div className="tl"
                        onMouseMove={(e) => TOOLTIPS[l] && setTipState({ label: l, def: TOOLTIPS[l], x: e.clientX, y: e.clientY })}
                        onMouseLeave={() => setTipState(null)}
                        style={TOOLTIPS[l] ? { cursor: "help", borderBottom: "1px dashed rgba(148,163,184,0.3)", display: "inline-block" } : {}}>
                        {l}
                      </div>
                      <div className="tv" style={{color:c}}>{v}</div>
                      <div className="ts">{s}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {rag && (
              <div className="pnl" style={{marginBottom:"12px"}}>
                <div className="ph">
                  <span className="pt">SEC Filing Analysis</span>
                  <span style={{fontFamily:"var(--mono)",fontSize:"9px",color:"var(--txt3)"}}>{result.agent_results.rag.filings_analyzed} filings analyzed</span>
                </div>
                <div className="pb"><p className="prose">{rag.sec_summary}</p></div>
              </div>
            )}

            <div className="foot">Not financial advice — for research and educational purposes only</div>
          </>
        )}
      </div>
    </>
  );
}