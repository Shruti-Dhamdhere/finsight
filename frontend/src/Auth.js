import { useState } from "react";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.REACT_APP_SUPABASE_URL,
  process.env.REACT_APP_SUPABASE_ANON_KEY
);

export { supabase };

const inputStyle = {
  width: "100%", padding: "12px 16px", borderRadius: "8px",
  background: "#13131a", border: "1px solid #1e1e2e",
  color: "#f1f5f9", fontSize: "14px", outline: "none",
  fontFamily: "Inter, sans-serif", marginBottom: "12px",
  boxSizing: "border-box"
};

const btnStyle = (primary) => ({
  width: "100%", padding: "12px", borderRadius: "8px",
  background: primary ? "#6366f1" : "#13131a",
  border: primary ? "none" : "1px solid #1e1e2e",
  color: primary ? "white" : "#94a3b8",
  fontWeight: 600, fontSize: "14px", cursor: "pointer",
  fontFamily: "Inter, sans-serif", marginBottom: "8px"
});

export default function Auth({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const handleEmailAuth = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      if (mode === "login") {
        const { data, error } = await supabase.auth.signInWithPassword({
          email, password
        });
        if (error) throw error;
        onAuth(data.session);
      } else {
        const { error } = await supabase.auth.signUp({
          email, password
        });
        if (error) throw error;
        setMessage("Check your email to confirm your account, then log in.");
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin }
    });
  };

  return (
    <div style={{
      minHeight: "100vh", background: "#0a0a0f",
      display: "flex", alignItems: "center", justifyContent: "center"
    }}>
      <div style={{
        background: "#13131a", border: "1px solid #1e1e2e",
        borderRadius: "16px", padding: "40px", width: "100%", maxWidth: "400px"
      }}>
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div style={{ fontWeight: 700, fontSize: "24px", color: "#f1f5f9" }}>FinSight</div>
          <div style={{ color: "#64748b", fontSize: "14px", marginTop: "4px" }}>
            {mode === "login" ? "Sign in to your account" : "Create your account"}
          </div>
        </div>

        {error && (
          <div style={{ background: "#2d0a0a", border: "1px solid #7f1d1d", borderRadius: "8px", padding: "12px", color: "#f87171", fontSize: "13px", marginBottom: "16px" }}>
            {error}
          </div>
        )}

        {message && (
          <div style={{ background: "#052e16", border: "1px solid #166534", borderRadius: "8px", padding: "12px", color: "#4ade80", fontSize: "13px", marginBottom: "16px" }}>
            {message}
          </div>
        )}

        <button onClick={handleGoogle} style={btnStyle(false)}>
          Continue with Google
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: "12px", margin: "16px 0" }}>
          <div style={{ flex: 1, height: "1px", background: "#1e1e2e" }} />
          <span style={{ color: "#475569", fontSize: "12px" }}>or</span>
          <div style={{ flex: 1, height: "1px", background: "#1e1e2e" }} />
        </div>

        <input
          type="email"
          placeholder="Email address"
          value={email}
          onChange={e => setEmail(e.target.value)}
          style={inputStyle}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleEmailAuth()}
          style={inputStyle}
        />

        <button
          onClick={handleEmailAuth}
          disabled={loading}
          style={btnStyle(true)}
        >
          {loading ? "Loading..." : mode === "login" ? "Sign In" : "Create Account"}
        </button>

        <div style={{ textAlign: "center", marginTop: "16px" }}>
          <span style={{ color: "#64748b", fontSize: "13px" }}>
            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          </span>
          <span
            onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(null); setMessage(null); }}
            style={{ color: "#6366f1", fontSize: "13px", cursor: "pointer" }}
          >
            {mode === "login" ? "Sign up" : "Sign in"}
          </span>
        </div>

        <div style={{ textAlign: "center", marginTop: "24px", padding: "12px", background: "#0a0a0f", borderRadius: "8px" }}>
          <div style={{ color: "#64748b", fontSize: "12px", marginBottom: "4px" }}>Free tier: 3 analyses/day</div>
          <div style={{ color: "#4ade80", fontSize: "12px" }}>FinSight Alpha: Unlimited — $9.99/month</div>
        </div>
      </div>
    </div>
  );
}