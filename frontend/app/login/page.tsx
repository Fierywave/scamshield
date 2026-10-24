"use client";
import { useState } from "react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function login() {
    setError("");
    try {
      const res = await fetch((process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        setError("Wrong email or password");
        return;
      }
      const data = await res.json();
      localStorage.setItem("token", data.token);
      window.location.href = "/cases";
    } catch {
      setError("Could not reach the API. Is Docker running?");
    }
  }

  const box = { display: "block", width: "100%", padding: 10, marginBottom: 10, fontSize: 16, boxSizing: "border-box" as const, background: "#fff", color: "#111", border: "1px solid #999" };

  return (
    <main style={{ maxWidth: 360, margin: "80px auto", padding: 16, fontFamily: "sans-serif", background: "#fff", color: "#111", minHeight: "100vh" }}>
      <h1>Analyst login</h1>
      <input style={box} placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input style={box} type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button onClick={login} style={{ padding: "10px 20px", fontSize: 16, cursor: "pointer" }}>Log in</button>
      {error && <p style={{ color: "#c62828" }}>{error}</p>}
    </main>
  );
}


