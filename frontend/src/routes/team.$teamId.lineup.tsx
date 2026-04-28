import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { HmApiError } from "../api/client";
import type { LineupSlots, Position, Skater, Goalie } from "../api/types";
import { Card } from "../components/Card";
import { Shell } from "../components/Shell";
import { useLeague } from "../queries/league";
import { useLineup, useUpdateLineup } from "../queries/lineup";
import { useRoster } from "../queries/teams";
import { attrClass } from "../lib/team-colors";

type SlotDef = { key: keyof LineupSlots; label: string; pos: Position | "G" };
const FORWARD_SLOTS: SlotDef[] = [
  { key: "line1_lw_id", pos: "LW", label: "L1" },
  { key: "line1_c_id", pos: "C", label: "L1" },
  { key: "line1_rw_id", pos: "RW", label: "L1" },
  { key: "line2_lw_id", pos: "LW", label: "L2" },
  { key: "line2_c_id", pos: "C", label: "L2" },
  { key: "line2_rw_id", pos: "RW", label: "L2" },
  { key: "line3_lw_id", pos: "LW", label: "L3" },
  { key: "line3_c_id", pos: "C", label: "L3" },
  { key: "line3_rw_id", pos: "RW", label: "L3" },
  { key: "line4_lw_id", pos: "LW", label: "L4" },
  { key: "line4_c_id", pos: "C", label: "L4" },
  { key: "line4_rw_id", pos: "RW", label: "L4" },
];
const DEF_SLOTS: SlotDef[] = [
  { key: "pair1_ld_id", pos: "LD", label: "D1" },
  { key: "pair1_rd_id", pos: "RD", label: "D1" },
  { key: "pair2_ld_id", pos: "LD", label: "D2" },
  { key: "pair2_rd_id", pos: "RD", label: "D2" },
  { key: "pair3_ld_id", pos: "LD", label: "D3" },
  { key: "pair3_rd_id", pos: "RD", label: "D3" },
];
const GOALIE_SLOTS: SlotDef[] = [
  { key: "starting_goalie_id", pos: "G", label: "Starter" },
  { key: "backup_goalie_id", pos: "G", label: "Backup" },
];
const ALL_SLOTS = [...FORWARD_SLOTS, ...DEF_SLOTS, ...GOALIE_SLOTS];

const skaterOvr = (p: Skater) =>
  Math.round(0.25 * p.shooting + 0.2 * p.passing + 0.2 * p.skating + 0.2 * p.defense + 0.15 * p.physical);
const goalieOvr = (g: Goalie) =>
  Math.round(0.3 * g.reflexes + 0.25 * g.positioning + 0.2 * g.rebound_control + 0.15 * g.puck_handling + 0.1 * g.mental);

const LineupEditor = () => {
  const { teamId } = Route.useParams();
  const id = Number(teamId);
  const league = useLeague();
  const lineup = useLineup(id);
  const roster = useRoster(id);
  const update = useUpdateLineup(id);
  const nav = useNavigate();
  const [draft, setDraft] = useState<LineupSlots | null>(null);
  const [active, setActive] = useState<keyof LineupSlots>("line1_lw_id");
  const [toast, setToast] = useState<{ type: "ok" | "err"; msg: string } | null>(null);

  useEffect(() => {
    if (lineup.data) {
      const { team_id: _ignored, ...slots } = lineup.data;
      setDraft(slots as LineupSlots);
    }
  }, [lineup.data]);

  if (!league.data || !roster.data || !draft) {
    return <Shell crumbs={["Continental Hockey League", "My Team", "Lineup Editor"]}>Loading…</Shell>;
  }
  if (league.data.user_team_id !== id) {
    return (
      <Shell crumbs={["Continental Hockey League", "My Team", "Lineup Editor"]}>
        <div style={{ color: "var(--ink-3)" }}>This is not your team.</div>
      </Shell>
    );
  }

  const skaterIds = [...FORWARD_SLOTS, ...DEF_SLOTS].map((s) => draft[s.key]);
  const goalieIds = GOALIE_SLOTS.map((s) => draft[s.key]);
  const skaterDups = new Set(
    skaterIds.filter((v, i) => skaterIds.indexOf(v) !== i),
  );
  const goalieDup = goalieIds[0] === goalieIds[1];
  const dupSlotKeys = new Set<keyof LineupSlots>();
  [...FORWARD_SLOTS, ...DEF_SLOTS].forEach((s) => {
    if (skaterDups.has(draft[s.key])) dupSlotKeys.add(s.key);
  });
  if (goalieDup) GOALIE_SLOTS.forEach((s) => dupSlotKeys.add(s.key));

  const activeDef = ALL_SLOTS.find((s) => s.key === active)!;
  const usedSet = new Set<number>(Object.values(draft));
  const candidates =
    activeDef.pos === "G"
      ? roster.data.goalies.map((g) => ({ id: g.id, name: g.name, age: g.age, ovr: goalieOvr(g), pos: "G" as const }))
      : roster.data.skaters
          .filter((s) => s.position === activeDef.pos)
          .map((s) => ({ id: s.id, name: s.name, age: s.age, ovr: skaterOvr(s), pos: s.position }));

  const playerName = (id: number) =>
    roster.data!.skaters.find((s) => s.id === id)?.name ?? roster.data!.goalies.find((g) => g.id === id)?.name;
  const playerOvr = (id: number) => {
    const sk = roster.data!.skaters.find((s) => s.id === id);
    if (sk) return skaterOvr(sk);
    const g = roster.data!.goalies.find((g) => g.id === id);
    return g ? goalieOvr(g) : null;
  };

  const assign = (newId: number) => setDraft({ ...draft, [active]: newId });

  const submit = async () => {
    if (dupSlotKeys.size) {
      setToast({ type: "err", msg: "Fix duplicate slot assignments before saving." });
      setTimeout(() => setToast(null), 4500);
      return;
    }
    try {
      await update.mutateAsync(draft);
      setToast({ type: "ok", msg: "Lineup saved." });
      setTimeout(() => nav({ to: "/team/$teamId", params: { teamId } }), 600);
    } catch (e) {
      setToast({ type: "err", msg: e instanceof HmApiError ? `${e.code}: ${e.message}` : String(e) });
      setTimeout(() => setToast(null), 4500);
    }
  };

  const Slot = ({ s }: { s: SlotDef }) => {
    const v = draft[s.key];
    const name = playerName(v);
    const ovr = playerOvr(v);
    const isActive = active === s.key;
    const isDup = dupSlotKeys.has(s.key);
    return (
      <div
        className={`slot ${!name ? "empty" : ""} ${isDup ? "dup" : ""}`}
        onClick={() => setActive(s.key)}
        style={{ outline: isActive ? "2px solid var(--navy-600)" : "none", outlineOffset: 1 }}
      >
        <span className="pos">{s.pos}</span>
        {name ? (
          <>
            <span className="nm">{name}</span>
            {ovr != null && <span className="ovr">{ovr}</span>}
          </>
        ) : (
          <span className="nm" style={{ color: "var(--ink-4)", fontWeight: 500 }}>
            Click to assign…
          </span>
        )}
      </div>
    );
  };

  return (
    <Shell
      crumbs={["Continental Hockey League", "My Team", "Lineup Editor"]}
      topRight={
        <button className="btn btn-primary" disabled={update.isPending} onClick={submit}>
          {update.isPending ? "Saving…" : "Save Lineup"}
        </button>
      }
    >
      <div className="section-h">
        <h1>Lineup Editor</h1>
        <span className="sub">Click a slot, then pick a player from the roster panel.</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 14 }}>
        <div>
          <Card title="Forwards" className="!mb-3">
            <div style={{ padding: "10px 14px" }}>
              {[0, 1, 2, 3].map((L) => (
                <div key={L} className="line-row">
                  <div className="lbl">L{L + 1}</div>
                  <Slot s={FORWARD_SLOTS[L * 3]} />
                  <Slot s={FORWARD_SLOTS[L * 3 + 1]} />
                  <Slot s={FORWARD_SLOTS[L * 3 + 2]} />
                </div>
              ))}
            </div>
          </Card>
          <Card title="Defense + Goalies" className="mt-3">
            <div style={{ padding: "10px 14px" }}>
              {[0, 1, 2].map((P) => (
                <div
                  key={P}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "28px 1fr 1fr",
                    gap: 8,
                    alignItems: "center",
                    padding: "4px 0",
                  }}
                >
                  <div className="lbl" style={{ font: "800 10px/1 'Roboto Condensed'", color: "var(--ink-3)", letterSpacing: "0.10em" }}>
                    D{P + 1}
                  </div>
                  <Slot s={DEF_SLOTS[P * 2]} />
                  <Slot s={DEF_SLOTS[P * 2 + 1]} />
                </div>
              ))}
              <div
                style={{
                  borderTop: "1px solid var(--line)",
                  marginTop: 8,
                  paddingTop: 10,
                  display: "grid",
                  gridTemplateColumns: "28px 1fr 1fr",
                  gap: 8,
                  alignItems: "center",
                }}
              >
                <div className="lbl" style={{ font: "800 10px/1 'Roboto Condensed'", color: "var(--ink-3)", letterSpacing: "0.10em" }}>
                  G
                </div>
                <Slot s={GOALIE_SLOTS[0]} />
                <Slot s={GOALIE_SLOTS[1]} />
              </div>
            </div>
          </Card>
        </div>

        <Card
          title={`Available · ${activeDef.pos}`}
          sub={`Slot ${activeDef.label} ${activeDef.pos}`}
        >
          <div style={{ maxHeight: 540, overflow: "auto" }}>
            {candidates.map((p) => {
              const taken = usedSet.has(p.id) && draft[active] !== p.id;
              const selected = draft[active] === p.id;
              return (
                <div
                  key={p.id}
                  className="bench-pl"
                  onClick={() => !taken && assign(p.id)}
                  style={{
                    background: selected ? "rgba(220,38,38,.10)" : "",
                    opacity: taken ? 0.5 : 1,
                    cursor: taken ? "not-allowed" : "pointer",
                  }}
                >
                  <span className="num">·</span>
                  <div>
                    <div className="nm">
                      {p.name}
                      {taken && (
                        <span
                          style={{
                            fontSize: 9,
                            color: "var(--red)",
                            marginLeft: 6,
                            fontWeight: 700,
                            letterSpacing: "0.08em",
                          }}
                        >
                          USED
                        </span>
                      )}
                    </div>
                    <div className="meta">
                      {p.pos} · Age {p.age}
                    </div>
                  </div>
                  <div className={`chip ${attrClass(p.ovr)}`}>{p.ovr}</div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {toast && (
        <div className="toast" style={{ borderLeftColor: toast.type === "ok" ? "var(--green)" : "var(--red)" }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="7" cy="7" r="6" />
            {toast.type === "ok" ? (
              <path d="M4 7l2 2 4-4" />
            ) : (
              <>
                <path d="M7 4v3" />
                <circle cx="7" cy="9.5" r=".5" fill="currentColor" />
              </>
            )}
          </svg>
          {toast.msg}
        </div>
      )}
    </Shell>
  );
};

export const Route = createFileRoute("/team/$teamId/lineup")({ component: LineupEditor });
