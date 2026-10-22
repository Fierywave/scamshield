"use client";
import { useState } from "react";

type Result = {
  verdict: string;
  score: number;
  urls: { url: string; probability: number }[];
  reasons: string[];
  report_id: number;
  case_id: number | null;
  case_size: number;
};

const COLORS: Record<string, string> = {
  scam: "#c62828",
  suspicious: "#ef6c00",
  "likely safe": "#2e7d32",
};

export default function Home() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function analyze() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch("http://localhost:8000/reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error("Server error " + res.status);
      setResult(await res.json());
    } catch {
      setError("Could not reach the API. Is Docker running?");
    }
    setLoading(false);
  }

  return (
    <main style={{ maxWidth: 700, margin: "40px auto", padding: 16, fontFamily: "sans-serif", background: "#fff", color: "#111", minHeight: "100vh" }}>
      <h1>ScamShield</h1>
      <p>Paste a suspicious SMS, WhatsApp message, or link.</p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={6}
        style={{ width: "100%", padding: 10, fontSize: 16, boxSizing: "border-box", background: "#fff", color: "#111", border: "1px solid #999" }}
        placeholder="Paste message here..."
      />
      <p style={{ fontSize: 13, color: "#555" }}>
        Messages you submit are saved so analysts can link related scams. Phone and account numbers are masked before saving. Please do not paste passwords or OTPs.
      </p>
      <button
        onClick={analyze}
        disabled={loading || !text.trim()}
        style={{ padding: "10px 20px", fontSize: 16, cursor: "pointer" }}
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>
      <a href="/cases" style={{ marginLeft: 16 }}>Analyst dashboard</a>

      {error && <p style={{ color: "#c62828" }}>{error}</p>}

      {result && (
        <div style={{ marginTop: 24, border: "2px solid " + COLORS[result.verdict], borderRadius: 8, padding: 16 }}>
          <h2 style={{ color: COLORS[result.verdict], margin: 0, textTransform: "capitalize" }}>
            {result.verdict}
          </h2>
          <p>Risk score: {Math.round(result.score * 100)} / 100</p>

          {result.case_id && (
            <p style={{ background: "#fff3e0", padding: 8, borderRadius: 6 }}>
              {result.case_size > 1
                ? `Linked to case #${result.case_id}: ${result.case_size} reports share evidence with this message.`
                : `Opened new case #${result.case_id} for analyst review.`}
            </p>
          )}

          {result.reasons.length > 0 && (
            <>
              <strong>Why:</strong>
              <ul>
                {result.reasons.map((r) => <li key={r}>{r}</li>)}
              </ul>
            </>
          )}
          {result.urls.length > 0 && (
            <>
              <strong>Links found:</strong>
              <ul>
                {result.urls.map((u) => (
                  <li key={u.url}>{u.url} (risk {Math.round(u.probability * 100)}%)</li>
                ))}
              </ul>
            </>
          )}
          <p style={{ fontSize: 13, color: "#555" }}>
            This is a decision aid, not a guarantee. Verify through your bank's official app or helpline.
          </p>
        </div>
      )}
    </main>
  );
}
