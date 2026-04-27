import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { HmApiError } from "../api/client";
import type { LineupSlots, Position } from "../api/types";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { InlineError } from "../components/Toast";
import { useLeague } from "../queries/league";
import { useLineup, useUpdateLineup } from "../queries/lineup";
import { useRoster } from "../queries/teams";

const FORWARD_SLOTS: { key: keyof LineupSlots; pos: Position; label: string }[] = [
  { key: "line1_lw_id", pos: "LW", label: "Line 1 LW" },
  { key: "line1_c_id", pos: "C", label: "Line 1 C" },
  { key: "line1_rw_id", pos: "RW", label: "Line 1 RW" },
  { key: "line2_lw_id", pos: "LW", label: "Line 2 LW" },
  { key: "line2_c_id", pos: "C", label: "Line 2 C" },
  { key: "line2_rw_id", pos: "RW", label: "Line 2 RW" },
  { key: "line3_lw_id", pos: "LW", label: "Line 3 LW" },
  { key: "line3_c_id", pos: "C", label: "Line 3 C" },
  { key: "line3_rw_id", pos: "RW", label: "Line 3 RW" },
  { key: "line4_lw_id", pos: "LW", label: "Line 4 LW" },
  { key: "line4_c_id", pos: "C", label: "Line 4 C" },
  { key: "line4_rw_id", pos: "RW", label: "Line 4 RW" },
];
const DEFENSE_SLOTS: { key: keyof LineupSlots; pos: Position; label: string }[] = [
  { key: "pair1_ld_id", pos: "LD", label: "Pair 1 LD" },
  { key: "pair1_rd_id", pos: "RD", label: "Pair 1 RD" },
  { key: "pair2_ld_id", pos: "LD", label: "Pair 2 LD" },
  { key: "pair2_rd_id", pos: "RD", label: "Pair 2 RD" },
  { key: "pair3_ld_id", pos: "LD", label: "Pair 3 LD" },
  { key: "pair3_rd_id", pos: "RD", label: "Pair 3 RD" },
];

const LineupEditor = () => {
  const { teamId } = Route.useParams();
  const id = Number(teamId);
  const league = useLeague();
  const lineup = useLineup(id);
  const roster = useRoster(id);
  const update = useUpdateLineup(id);
  const nav = useNavigate();
  const [draft, setDraft] = useState<LineupSlots | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (lineup.data) {
      const { team_id: _ignored, ...slots } = lineup.data;
      setDraft(slots as LineupSlots);
    }
  }, [lineup.data]);

  if (!league.data || !roster.data || !draft) return <div>Loading…</div>;
  if (league.data.user_team_id !== id) return <div>This is not your team.</div>;

  const set = (k: keyof LineupSlots, v: number) => setDraft((d) => ({ ...d!, [k]: v }));
  const skatersByPos = (p: Position) => roster.data!.skaters.filter((s) => s.position === p);

  const skaterIds = [...FORWARD_SLOTS, ...DEFENSE_SLOTS].map((s) => draft[s.key]);
  const dupSkater = new Set(skaterIds).size !== skaterIds.length;
  const dupGoalie = draft.starting_goalie_id === draft.backup_goalie_id;

  const submit = async () => {
    setErr(null);
    try {
      await update.mutateAsync(draft);
      nav({ to: "/team/$teamId", params: { teamId } });
    } catch (e) {
      if (e instanceof HmApiError) setErr(`${e.code}: ${e.message}`);
      else throw e;
    }
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <h2 className="text-xl font-bold">Lineup</h2>
      <Card title="Forwards">
        <div className="grid grid-cols-3 gap-2">
          {FORWARD_SLOTS.map((s) => (
            <label key={s.key} className="text-sm">
              <span className="block text-slate-500">{s.label}</span>
              <select
                className="border rounded px-1 py-1 w-full"
                value={draft[s.key]}
                onChange={(e) => set(s.key, Number(e.target.value))}
              >
                {skatersByPos(s.pos).map((sk) => (
                  <option key={sk.id} value={sk.id}>{sk.name}</option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </Card>
      <Card title="Defense">
        <div className="grid grid-cols-2 gap-2">
          {DEFENSE_SLOTS.map((s) => (
            <label key={s.key} className="text-sm">
              <span className="block text-slate-500">{s.label}</span>
              <select
                className="border rounded px-1 py-1 w-full"
                value={draft[s.key]}
                onChange={(e) => set(s.key, Number(e.target.value))}
              >
                {skatersByPos(s.pos).map((sk) => (
                  <option key={sk.id} value={sk.id}>{sk.name}</option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </Card>
      <Card title="Goalies">
        <div className="grid grid-cols-2 gap-2">
          {(["starting_goalie_id", "backup_goalie_id"] as const).map((k) => (
            <label key={k} className="text-sm">
              <span className="block text-slate-500">{k === "starting_goalie_id" ? "Starter" : "Backup"}</span>
              <select
                className="border rounded px-1 py-1 w-full"
                value={draft[k]}
                onChange={(e) => set(k, Number(e.target.value))}
              >
                {roster.data!.goalies.map((g) => (
                  <option key={g.id} value={g.id}>{g.name}</option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </Card>
      {dupSkater && <InlineError>A skater appears in multiple slots.</InlineError>}
      {dupGoalie && <InlineError>Starter and backup goalie must differ.</InlineError>}
      {err && <InlineError>{err}</InlineError>}
      <Button onClick={submit} disabled={dupSkater || dupGoalie || update.isPending}>
        {update.isPending ? "Saving…" : "Save lineup"}
      </Button>
    </div>
  );
};

export const Route = createFileRoute("/team/$teamId/lineup")({ component: LineupEditor });
