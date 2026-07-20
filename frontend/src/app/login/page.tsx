"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";

export default function LoginPage() {
  const router = useRouter();
  const [loginIdentifier, setLoginIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login(loginIdentifier, password);
      router.push(user.user_type === "volunteer" ? "/volunteer" : "/cities");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--canvas)",
        padding: 20,
      }}
    >
      <form
        onSubmit={onSubmit}
        style={{
          width: 380,
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--r-2xl)",
          padding: "36px 32px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 28 }}>
          <span style={{ width: 15, height: 15, borderRadius: "50%", background: "var(--accent)" }} />
          <span style={{ font: "var(--w-black) 15px/1 var(--font)", letterSpacing: "0.01em" }}>Small World</span>
        </div>
        <h1 style={{ font: "var(--w-black) 26px/1.2 var(--font)", letterSpacing: "-0.02em", margin: "0 0 6px" }}>
          Sign in
        </h1>
        <p style={{ font: "var(--w-medium) 14px/1.5 var(--font)", color: "var(--text-muted)", margin: "0 0 24px" }}>
          Staff and volunteers use the same door.
        </p>

        <label style={{ display: "block", font: "var(--w-semibold) 12.5px/1 var(--font)", color: "var(--text-muted)", marginBottom: 6 }}>
          Phone or username
        </label>
        <input
          value={loginIdentifier}
          onChange={(e) => setLoginIdentifier(e.target.value)}
          autoFocus
          style={{
            width: "100%",
            font: "var(--w-semibold) 15px/1 var(--font)",
            padding: "12px 14px",
            border: "2px solid var(--ink)",
            borderRadius: "var(--r-lg)",
            marginBottom: 16,
            outline: "none",
            background: "var(--surface)",
            color: "var(--ink)",
          }}
        />

        <label style={{ display: "block", font: "var(--w-semibold) 12.5px/1 var(--font)", color: "var(--text-muted)", marginBottom: 6 }}>
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{
            width: "100%",
            font: "var(--w-semibold) 15px/1 var(--font)",
            padding: "12px 14px",
            border: "2px solid var(--ink)",
            borderRadius: "var(--r-lg)",
            marginBottom: 20,
            outline: "none",
            background: "var(--surface)",
            color: "var(--ink)",
          }}
        />

        {error ? (
          <div
            style={{
              font: "var(--w-semibold) 13px/1.4 var(--font)",
              color: "var(--warn-ink)",
              background: "var(--warn-bg)",
              borderRadius: "var(--r-md)",
              padding: "10px 12px",
              marginBottom: 16,
            }}
          >
            {error}
          </div>
        ) : null}

        <Button type="submit" variant="primary" size="lg" block disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
