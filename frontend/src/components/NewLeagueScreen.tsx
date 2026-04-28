import { useState } from "react";
import { useCreateLeague } from "../queries/league";

export const NewLeagueScreen = () => {
  const [seed, setSeed] = useState<string>("");
  const create = useCreateLeague();
  return (
    <div
      className="card"
      style={{ width: "100%", maxWidth: 480, padding: 0, overflow: "hidden" }}
    >
      <div className="ribbon-h">
        <span className="accent" />
        Continental Hockey League · Manager '26
      </div>
      <div style={{ padding: "20px 22px" }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Start a new league</h2>
        <p style={{ color: "var(--ink-3)", fontSize: 12, marginTop: 6 }}>
          Generate 4 teams and an 18-game schedule.
        </p>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginTop: 14 }}>
          <label style={{ flex: 1, fontSize: 11, color: "var(--ink-3)", fontWeight: 600 }}>
            <span style={{ display: "block", marginBottom: 4, letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Seed
            </span>
            <input
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="random"
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
            disabled={create.isPending}
            onClick={() => create.mutate(seed ? Number(seed) : undefined)}
          >
            {create.isPending ? "Generating…" : "Create League"}
          </button>
        </div>
      </div>
    </div>
  );
};
