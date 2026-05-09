import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useCreateManager } from "../queries/manager";

export const CreateManagerScreen = () => {
  const [name, setName] = useState("");
  const create = useCreateManager();
  const nav = useNavigate();

  const submit = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    create.mutate(trimmed, {
      onSuccess: () => nav({ to: "/manager/choose-team" }),
    });
  };

  return (
    <div
      className="card"
      style={{ width: "100%", maxWidth: 480, padding: 0, overflow: "hidden" }}
    >
      <div className="ribbon-h">
        <span className="accent" />
        Welcome, Coach
      </div>
      <div style={{ padding: "20px 22px" }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Create your manager</h2>
        <p style={{ color: "var(--ink-3)", fontSize: 12, marginTop: 6 }}>
          What should we call you? You'll then choose which team to manage.
        </p>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginTop: 14 }}>
          <label style={{ flex: 1, fontSize: 11, color: "var(--ink-3)", fontWeight: 600 }}>
            <span style={{ display: "block", marginBottom: 4, letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Name
            </span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Pat Quinn"
              maxLength={64}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") submit();
              }}
              style={{
                width: "100%",
                border: "1px solid var(--line)",
                background: "var(--surface)",
                borderRadius: 4,
                padding: "8px 10px",
                font: "500 13px/1.2 'Inter', sans-serif",
                color: "var(--ink)",
              }}
            />
          </label>
          <button
            className="btn btn-primary"
            disabled={create.isPending || !name.trim()}
            onClick={submit}
          >
            {create.isPending ? "Saving…" : "Continue →"}
          </button>
        </div>
      </div>
    </div>
  );
};
