import { useState } from "react";

import { Button } from "./Button";

type Props = {
  player: { id: number; name: string; ovr: number };
  defaultSalary: number;
  onClose: () => void;
  onSubmit: (terms: { length: number; salary: number; no_trade_clause: boolean }) => void;
  submitting?: boolean;
};

export const SignContractModal = ({
  player,
  defaultSalary,
  onClose,
  onSubmit,
  submitting,
}: Props) => {
  const [length, setLength] = useState(2);
  const [salary, setSalary] = useState(defaultSalary);
  const [ntc, setNtc] = useState(false);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.55)",
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{ width: 380, maxWidth: "90vw", padding: 20 }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ margin: 0, marginBottom: 4 }}>Sign {player.name}</h2>
        <div className="sub" style={{ marginBottom: 14 }}>OVR {player.ovr}</div>

        <label style={{ display: "block", marginBottom: 12 }}>
          <span style={{ display: "block", fontSize: 12, color: "var(--ink-3)", marginBottom: 4 }}>
            Length (years)
          </span>
          <select
            value={length}
            onChange={(e) => setLength(Number(e.target.value))}
            style={{ width: "100%" }}
          >
            {[1, 2, 3, 4, 5, 6, 7, 8].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>

        <label style={{ display: "block", marginBottom: 12 }}>
          <span style={{ display: "block", fontSize: 12, color: "var(--ink-3)", marginBottom: 4 }}>
            Salary (${(salary / 1000).toFixed(2)}M / yr)
          </span>
          <input
            type="number"
            min={750}
            max={15000}
            step={50}
            value={salary}
            onChange={(e) => setSalary(Number(e.target.value))}
            style={{ width: "100%" }}
          />
        </label>

        <label style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 16 }}>
          <input type="checkbox" checked={ntc} onChange={(e) => setNtc(e.target.checked)} />
          <span style={{ fontSize: 13 }}>No-Trade Clause</span>
        </label>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button variant="default" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={() => onSubmit({ length, salary, no_trade_clause: ntc })}
            disabled={submitting}
          >
            Sign
          </Button>
        </div>
      </div>
    </div>
  );
};
