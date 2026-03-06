// frontend/src/Onboarding.js
// Drop-in onboarding modal for FinSight
// Matches existing CSS variables exactly — no new fonts or colors needed
//
// Usage in App.js:
//   import Onboarding from "./Onboarding";
//
//   // After the auth check, before the main return:
//   if (session && profile && !profile.onboarding_complete) {
//     return <><style>{css}</style><Onboarding session={session} onComplete={(p) => setProfile({...profile, ...p, onboarding_complete: true})} /></>
//   }

import { useState } from "react";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const STEPS = [
  {
    id: "experience",
    question: "How familiar are you with investing?",
    sub: "This helps us explain things at the right level — no jargon if you're new.",
    options: [
      { value: "beginner",     label: "Just starting out",         desc: "I've never bought a stock before" },
      { value: "intermediate", label: "Some experience",           desc: "I've invested a few times before" },
      { value: "experienced",  label: "Comfortable with markets",  desc: "I understand P/E, RSI, earnings reports" },
    ],
  },
  {
    id: "goal",
    question: "What's your main reason for investing?",
    sub: "We'll tailor recommendations to what actually matters to you.",
    options: [
      { value: "grow_savings", label: "Grow my savings",     desc: "Build wealth over the long term" },
      { value: "income",       label: "Generate income",     desc: "Dividends and regular returns" },
      { value: "learn",        label: "Learn as I go",       desc: "Understand markets while getting started" },
    ],
  },
  {
    id: "monthly_investable",
    question: "How much could you invest each month?",
    sub: "We'll size recommendations to what's realistic for you.",
    options: [
      { value: "under_200", label: "Under $200",       desc: "Starting small, building the habit" },
      { value: "200_500",   label: "$200 – $500",      desc: "Steady monthly contributions" },
      { value: "500_plus",  label: "More than $500",   desc: "Serious about building a portfolio" },
    ],
  },
  {
    id: "risk_tolerance",
    question: "How do you feel about risk?",
    sub: "There's no wrong answer — we just need to know how to calibrate our recommendations.",
    options: [
      { value: "low",    label: "Protect what I have",       desc: "I can't afford to lose money right now" },
      { value: "medium", label: "Some ups and downs are fine", desc: "I'm in it for the long term" },
      { value: "high",   label: "Higher risk, higher reward",  desc: "I'm okay with volatility" },
    ],
  },
];

const onboardingCSS = `
  .ob-overlay {
    position: fixed; inset: 0; z-index: 1000;
    background: rgba(6,8,15,0.92);
    backdrop-filter: blur(12px);
    display: flex; align-items: center; justify-content: center;
    padding: 24px;
  }

  .ob-card {
    background: var(--s1);
    border: 1px solid var(--b2);
    border-radius: 12px;
    width: 100%; max-width: 520px;
    padding: 40px;
    position: relative;
    box-shadow: 0 32px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(148,163,184,0.06);
    animation: ob-in 0.25s ease;
  }
  @keyframes ob-in {
    from { opacity: 0; transform: translateY(12px) scale(0.98); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
  }

  .ob-progress {
    display: flex; gap: 6px; margin-bottom: 36px;
  }
  .ob-prog-dot {
    height: 2px; flex: 1; border-radius: 2px;
    background: var(--b2);
    transition: background 0.3s;
  }
  .ob-prog-dot.done { background: var(--blue); }
  .ob-prog-dot.active { background: var(--blue-l); }

  .ob-step-tag {
    font-family: var(--mono); font-size: 10px;
    color: var(--blue-l); letter-spacing: 0.1em;
    text-transform: uppercase; margin-bottom: 10px;
  }

  .ob-q {
    font-size: 20px; font-weight: 600;
    color: var(--txt); line-height: 1.3;
    letter-spacing: -0.02em; margin-bottom: 8px;
  }

  .ob-sub {
    font-size: 13px; color: var(--txt2);
    line-height: 1.6; margin-bottom: 28px;
  }

  .ob-options { display: flex; flex-direction: column; gap: 10px; margin-bottom: 32px; }

  .ob-opt {
    display: flex; align-items: flex-start; gap: 14px;
    padding: 14px 16px; border-radius: 8px;
    border: 1px solid var(--b2);
    background: var(--s2);
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s, transform 0.1s;
  }
  .ob-opt:hover { border-color: var(--b3); background: var(--s3); }
  .ob-opt:active { transform: scale(0.99); }
  .ob-opt.selected {
    border-color: rgba(59,130,246,0.5);
    background: rgba(59,130,246,0.07);
  }

  .ob-radio {
    width: 16px; height: 16px; border-radius: 50%;
    border: 1.5px solid var(--b3);
    flex-shrink: 0; margin-top: 2px;
    display: flex; align-items: center; justify-content: center;
    transition: border-color 0.15s;
  }
  .ob-opt.selected .ob-radio {
    border-color: var(--blue);
    background: var(--blue);
  }
  .ob-radio-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: white; opacity: 0;
    transition: opacity 0.15s;
  }
  .ob-opt.selected .ob-radio-dot { opacity: 1; }

  .ob-opt-text { flex: 1; }
  .ob-opt-label {
    font-size: 13px; font-weight: 500;
    color: var(--txt); margin-bottom: 2px;
  }
  .ob-opt-desc { font-size: 11px; color: var(--txt3); }

  .ob-footer { display: flex; justify-content: space-between; align-items: center; }

  .ob-btn-back {
    padding: 9px 18px; border-radius: 6px;
    background: transparent; border: 1px solid var(--b2);
    color: var(--txt2); font-size: 12px; font-weight: 500;
    cursor: pointer; font-family: var(--sans);
    transition: color 0.15s, border-color 0.15s;
  }
  .ob-btn-back:hover { color: var(--txt); border-color: var(--b3); }

  .ob-btn-next {
    padding: 9px 22px; border-radius: 6px;
    background: var(--blue); border: none;
    color: #fff; font-size: 12px; font-weight: 500;
    cursor: pointer; font-family: var(--sans);
    transition: opacity 0.15s, transform 0.15s;
    box-shadow: 0 2px 12px rgba(59,130,246,0.25);
  }
  .ob-btn-next:hover:not(:disabled) { opacity: 0.88; transform: translateY(-1px); }
  .ob-btn-next:disabled {
    background: var(--s3); color: var(--txt3);
    cursor: not-allowed; box-shadow: none;
  }

  .ob-saving {
    display: flex; align-items: center; justify-content: center;
    gap: 10px; padding: 20px 0;
    color: var(--txt2); font-size: 13px;
  }
  .ob-spin {
    width: 16px; height: 16px; border-radius: 50%;
    border: 2px solid var(--b2);
    border-top-color: var(--blue);
    animation: ob-spin 0.7s linear infinite;
  }
  @keyframes ob-spin { to { transform: rotate(360deg); } }

  .ob-welcome {
    text-align: center; padding: 16px 0 8px;
    animation: ob-in 0.3s ease;
  }
  .ob-welcome-icon {
    width: 52px; height: 52px; border-radius: 12px;
    background: linear-gradient(135deg, #1e40af, #3b82f6);
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 20px;
  }
  .ob-welcome-title {
    font-size: 22px; font-weight: 600;
    color: var(--txt); letter-spacing: -0.02em;
    margin-bottom: 10px;
  }
  .ob-welcome-sub {
    font-size: 13px; color: var(--txt2);
    line-height: 1.7; max-width: 360px;
    margin: 0 auto 28px;
  }
  .ob-welcome-start {
    padding: 11px 28px; border-radius: 6px;
    background: var(--blue); border: none;
    color: #fff; font-size: 13px; font-weight: 500;
    cursor: pointer; font-family: var(--sans);
    transition: opacity 0.15s, transform 0.15s;
    box-shadow: 0 2px 16px rgba(59,130,246,0.3);
  }
  .ob-welcome-start:hover { opacity: 0.88; transform: translateY(-1px); }
  .ob-skip {
    display: block; margin-top: 14px;
    font-size: 11px; color: var(--txt3);
    cursor: pointer; background: none; border: none;
    font-family: var(--sans);
  }
  .ob-skip:hover { color: var(--txt2); }
`;

export default function Onboarding({ session, onComplete }) {
  const [phase, setPhase]     = useState("welcome"); // welcome | questions | saving
  const [step, setStep]       = useState(0);
  const [answers, setAnswers] = useState({
    experience: "", goal: "", monthly_investable: "", risk_tolerance: ""
  });

  const current    = STEPS[step];
  const selected   = answers[current?.id];
  const isLast     = step === STEPS.length - 1;

  const select = (value) => {
    setAnswers(a => ({ ...a, [current.id]: value }));
  };

  const next = async () => {
    if (!selected) return;
    if (!isLast) {
      setStep(s => s + 1);
      return;
    }
    // Last step — save profile
    setPhase("saving");
    try {
      const r = await fetch(`${API_URL}/profile`, {
        method:  "POST",
        headers: {
          "Content-Type":  "application/json",
          Authorization:   `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(answers),
      });
      if (!r.ok) throw new Error("Save failed");
      const saved = await r.json();
      onComplete(saved);
    } catch {
      // On error, skip onboarding so user isn't blocked
      onComplete({ ...answers, onboarding_complete: true });
    }
  };

  const back = () => { if (step > 0) setStep(s => s - 1); };

  const skip = () => {
    // Save defaults silently
    fetch(`${API_URL}/profile`, {
      method:  "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization:  `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        experience: "beginner", goal: "grow_savings",
        monthly_investable: "200_500", risk_tolerance: "medium",
      }),
    }).catch(() => {});
    onComplete({ onboarding_complete: true });
  };

  return (
    <>
      <style>{onboardingCSS}</style>
      <div className="ob-overlay">
        <div className="ob-card">

          {/* Welcome screen */}
          {phase === "welcome" && (
            <div className="ob-welcome">
              <div className="ob-welcome-icon">
                <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                  <polyline points="2,17 7,10 12,13 20,4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className="ob-welcome-title">Welcome to FinSight</div>
              <div className="ob-welcome-sub">
                Before you start, answer 4 quick questions so we can personalise
                every analysis to your situation — your experience, goals, and
                how much you want to invest.
              </div>
              <button className="ob-welcome-start" onClick={() => setPhase("questions")}>
                Get started — takes 30 seconds
              </button>
              <button className="ob-skip" onClick={skip}>Skip for now</button>
            </div>
          )}

          {/* Questions */}
          {phase === "questions" && (
            <>
              {/* Progress bar */}
              <div className="ob-progress">
                {STEPS.map((_, i) => (
                  <div
                    key={i}
                    className={`ob-prog-dot ${i < step ? "done" : i === step ? "active" : ""}`}
                  />
                ))}
              </div>

              <div className="ob-step-tag">Step {step + 1} of {STEPS.length}</div>
              <div className="ob-q">{current.question}</div>
              <div className="ob-sub">{current.sub}</div>

              <div className="ob-options">
                {current.options.map(opt => (
                  <div
                    key={opt.value}
                    className={`ob-opt ${selected === opt.value ? "selected" : ""}`}
                    onClick={() => select(opt.value)}
                  >
                    <div className="ob-radio">
                      <div className="ob-radio-dot" />
                    </div>
                    <div className="ob-opt-text">
                      <div className="ob-opt-label">{opt.label}</div>
                      <div className="ob-opt-desc">{opt.desc}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="ob-footer">
                {step > 0
                  ? <button className="ob-btn-back" onClick={back}>Back</button>
                  : <span />
                }
                <button
                  className="ob-btn-next"
                  onClick={next}
                  disabled={!selected}
                >
                  {isLast ? "Save my profile" : "Continue"}
                </button>
              </div>
            </>
          )}

          {/* Saving */}
          {phase === "saving" && (
            <div className="ob-saving">
              <div className="ob-spin" />
              Saving your profile…
            </div>
          )}

        </div>
      </div>
    </>
  );
}