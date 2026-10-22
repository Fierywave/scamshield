"use client";
import { useEffect, useState } from "react";

type CaseRow = { id: number; status: string; reports: number; max_score: number };
type Detail = {
  id: number;
  status: string;
  reports: { id: number; text: string; verdict: string; score: number; reasons: string[] }[];
  shared_evidence: { kind: string; value: string; reports: number }[];
};

const API = "http://localhost:8000";
const STATUS_COLORS: Record<string, string> = {
  under_review: "#ef6c00",
  confirmed: "#c62828",
  rejected: "#2e7d32",
};

export default function Cases() {
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState("");

  async function loadCases() {
    try {
      const res = await fetch(API + "/cases");
      setCases(await res.json());
      setError("");
    } catch {
      setError("Could not reach the API. Is Docker running?");
    }
  }

  async function open(id: number) {
    const res = await fetch(API + "/cases/" + id);
    setDetail(await res.json());
  }

  async function setStatus(id: number, status: string) {
    await fetch(API + "/cases/" + id, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    await loadCases();
    await open(id);
  }

  useEffect(() => {
    loadCases();
  }, []);

  const count = (s: string) => cases.filter((c) => c.status === s).length;

  return (
    <main style={{ maxWidth: 1000, margin: "30px auto", padding: 16, fontFamily: "sans-serif", background: "#fff", color: "#111", minHeight: "100vh" }}>
      <h1>Analyst Dashboard</h1>
      <p>
        Cases: {cases.length} | Under review: {count("under_review")} | Confirmed: {count("confirmed")} | Rejected: {count("rejected")}
      </p>
      {error && <p style={{ color: "#c62828" }}>{error}</p>}

      <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <h3>Cases</h3>
          {cases.length === 0 && <p>No cases yet.</p>}
          {cases.map((c) => (
            <div
              key={c.id}
              onClick={() => open(c.id)}
              style={{ border: "1px solid #ccc", borderRadius: 6, padding: 10, marginBottom: 8, cursor: "pointer", background: detail?.id === c.id ? "#f0f4ff" : "#fff" }}
            >
              <strong>Case #{c.id}</strong>{" "}
              <span style={{ color: STATUS_COLORS[c.status] }}>{c.status.replace("_", " ")}</span>
              <div style={{ fontSize: 13 }}>
                {c.reports} report(s), top risk {Math.round(c.max_score * 100)}/100
              </div>
            </div>
          ))}
        </div>

        <div style={{ flex: 2 }}>
          {!detail && <p>Select a case to see its evidence.</p>}
          {detail && (
            <>
              <h3>Case #{detail.id}</h3>
              <div style={{ marginBottom: 10 }}>
                {["under_review", "confirmed", "rejected"].map((s) => (
                  <button
                    key={s}
                    onClick={() => setStatus(detail.id, s)}
                    disabled={detail.status === s}
                    style={{ marginRight: 8, padding: "6px 12px", cursor: "pointer" }}
                  >
                    {s.replace("_", " ")}
                  </button>
                ))}
              </div>

              <strong>Shared evidence</strong>
              {detail.shared_evidence.length === 0 ? (
                <p>None shared between reports.</p>
              ) : (
                <ul>
                  {detail.shared_evidence.map((e) => (
                    <li key={e.kind + e.value}>
                      {e.kind}: {e.value} (in {e.reports} reports)
                    </li>
                  ))}
                </ul>
              )}

              <strong>Reports</strong>
              {detail.reports.map((r) => (
                <div key={r.id} style={{ border: "1px solid #ddd", borderRadius: 6, padding: 10, margin: "8px 0" }}>
                  <div style={{ fontSize: 13 }}>
                    Report #{r.id} | {r.verdict} | risk {Math.round(r.score * 100)}/100
                  </div>
                  <div style={{ margin: "6px 0" }}>{r.text}</div>
                  <ul style={{ fontSize: 13, margin: 0 }}>
                    {r.reasons.map((x) => <li key={x}>{x}</li>)}
                  </ul>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </main>
  );
}
