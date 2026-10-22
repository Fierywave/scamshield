"use client";
import { useEffect, useState } from "react";

const API = "http://localhost:8000";

type Metrics = {
  transactions: {
    total: number; flagged: number; fraud: number; tp: number; fp: number; fn: number;
    precision: number | null; recall: number | null; false_positive_rate: number | null;
    p50_ms: number | null; p99_ms: number | null;
  };
  by_pattern: { pattern: string; fraud: number; caught: number; recall: number | null }[];
  reports: Record<string, number>;
  cases: Record<string, number>;
};

type Flagged = {
  id: number; user_id: number; amount: number; pattern: string; is_fraud: number;
  ml_prob: number; rule_hit: number; reasons: string;
};

async function authFetch(url: string) {
  const token = localStorage.getItem("token");
  if (!token) {
    window.location.href = "/login";
    throw new Error("not logged in");
  }
  const res = await fetch(url, { headers: { Authorization: "Bearer " + token } });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("session expired");
  }
  return res;
}

const pct = (x: number | null) => (x === null ? "n/a" : (x * 100).toFixed(1) + "%");
const ms = (x: number | null) => (x === null ? "n/a" : x.toFixed(1) + " ms");

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: "1px solid #ccc", borderRadius: 8, padding: 12, minWidth: 140 }}>
      <div style={{ fontSize: 13, color: "#555" }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 600 }}>{value}</div>
    </div>
  );
}

export default function MetricsPage() {
  const [m, setM] = useState<Metrics | null>(null);
  const [flagged, setFlagged] = useState<Flagged[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const a = await authFetch(API + "/metrics");
        const b = await authFetch(API + "/transactions/flagged");
        if (!a.ok || !b.ok) throw new Error("bad response");
        setM(await a.json());
        setFlagged(await b.json());
      } catch {
        setError("Could not load metrics. Is Docker running?");
      }
    })();
  }, []);

  const th = { textAlign: "left" as const, padding: 6, borderBottom: "1px solid #ccc" };
  const td = { padding: 6, borderBottom: "1px solid #eee", fontSize: 14 };

  return (
    <main style={{ maxWidth: 1000, margin: "30px auto", padding: 16, fontFamily: "sans-serif", background: "#fff", color: "#111", minHeight: "100vh" }}>
      <h1>Model Metrics</h1>
      <a href="/cases">Back to cases</a>
      {error && <p style={{ color: "#c62828" }}>{error}</p>}

      {m && (
        <>
          <p style={{ fontSize: 13, color: "#555" }}>
            Transaction results come from a simulated stream, not real bank data. Fraud labels are known only because we generated them.
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", margin: "16px 0" }}>
            <Card label="Transactions scored" value={String(m.transactions.total)} />
            <Card label="Precision" value={pct(m.transactions.precision)} />
            <Card label="Recall" value={pct(m.transactions.recall)} />
            <Card label="False-positive rate" value={pct(m.transactions.false_positive_rate)} />
            <Card label="Latency p50" value={ms(m.transactions.p50_ms)} />
            <Card label="Latency p99" value={ms(m.transactions.p99_ms)} />
          </div>

          <h3>Recall by fraud pattern</h3>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead><tr><th style={th}>Pattern</th><th style={th}>Fraud</th><th style={th}>Caught</th><th style={th}>Recall</th></tr></thead>
            <tbody>
              {m.by_pattern.map((p) => (
                <tr key={p.pattern}>
                  <td style={td}>{p.pattern}</td><td style={td}>{p.fraud}</td>
                  <td style={td}>{p.caught}</td><td style={td}>{pct(p.recall)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Reports and cases</h3>
          <p>
            Reports: {Object.entries(m.reports).map(([k, v]) => `${k} ${v}`).join(" | ") || "none"}
            <br />
            Cases: {Object.entries(m.cases).map(([k, v]) => `${k.replace("_", " ")} ${v}`).join(" | ") || "none"}
          </p>

          <h3>Latest flagged transactions</h3>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr><th style={th}>User</th><th style={th}>Amount</th><th style={th}>Model prob</th><th style={th}>Why flagged</th><th style={th}>Actually fraud</th></tr>
            </thead>
            <tbody>
              {flagged.map((f) => (
                <tr key={f.id}>
                  <td style={td}>{f.user_id}</td>
                  <td style={td}>Rs {Math.round(f.amount)}</td>
                  <td style={td}>{f.ml_prob.toFixed(2)}</td>
                  <td style={td}>{f.reasons}</td>
                  <td style={td}>{f.is_fraud ? "yes (" + f.pattern + ")" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </main>
  );
}
