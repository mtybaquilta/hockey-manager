import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";

import { Button } from "../components/Button";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { skaterOvr } from "../lib/roster-tags";
import { attrClass } from "../lib/team-colors";
import type { PlayerKind, TradeBlockEntry } from "../api/types";
import { useLeague } from "../queries/league";
import { useRoster } from "../queries/teams";
import { useProposeTrade, useTradeBlock } from "../queries/trades";

const TradeOfferPanel = ({
  entry,
  userTeamId,
  onClose,
}: {
  entry: TradeBlockEntry;
  userTeamId: number;
  onClose: () => void;
}) => {
  const roster = useRoster(userTeamId);
  const propose = useProposeTrade(userTeamId);
  const [offeredId, setOfferedId] = useState<number | null>(null);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const candidates = useMemo(() => {
    if (!roster.data) return [] as { id: number; label: string; ovr: number }[];
    if (entry.player_type === "skater") {
      return roster.data.skaters
        .filter((s) => entry.position == null || s.position === entry.position)
        .map((s) => ({ id: s.id, label: `${s.name} (${s.position})`, ovr: skaterOvr(s) }))
        .sort((a, b) => b.ovr - a.ovr);
    }
    return roster.data.goalies
      .map((g) => ({
        id: g.id,
        label: `${g.name} (G)`,
        ovr: Math.round(
          0.3 * g.reflexes + 0.25 * g.positioning + 0.2 * g.rebound_control + 0.15 * g.puck_handling + 0.1 * g.mental,
        ),
      }))
      .sort((a, b) => b.ovr - a.ovr);
  }, [roster.data, entry.player_type, entry.position]);

  const offered = candidates.find((c) => c.id === offeredId);

  const submit = () => {
    if (offeredId == null) return;
    setResult(null);
    propose.mutate(
      {
        target_player_type: entry.player_type,
        target_player_id: entry.player_id,
        offered_player_type: entry.player_type,
        offered_player_id: offeredId,
      },
      {
        onSuccess: (res) => setResult({ ok: res.accepted, msg: res.message }),
        onError: (err: unknown) => {
          const m = err instanceof Error ? err.message : "Trade failed.";
          setResult({ ok: false, msg: m });
        },
      },
    );
  };

  return (
    <tr>
      <Td colSpan={9} style={{ background: "var(--bone)" }}>
        <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap", padding: "10px 4px" }}>
          <div>
            <div style={{ fontSize: 11, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: ".06em" }}>
              Target
            </div>
            <div style={{ fontWeight: 700 }}>
              {entry.name} ({entry.position ?? "G"}, age {entry.age}){" "}
              <span className={`chip ovr ${attrClass(entry.ovr)}`}>{entry.ovr}</span>
            </div>
            <div style={{ fontSize: 11, color: "var(--ink-3)" }}>asking value {entry.asking_value}</div>
          </div>
          <span style={{ color: "var(--ink-3)" }}>↔</span>
          <div>
            <div style={{ fontSize: 11, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: ".06em" }}>
              Your offer
            </div>
            <select
              value={offeredId ?? ""}
              onChange={(e) => setOfferedId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Select a player…</option>
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label} — OVR {c.ovr}
                </option>
              ))}
            </select>
            {offered && (
              <span style={{ marginLeft: 8 }}>
                <span className={`chip ovr ${attrClass(offered.ovr)}`}>{offered.ovr}</span>
              </span>
            )}
          </div>
          <Button onClick={submit} disabled={offeredId == null || propose.isPending}>
            {propose.isPending ? "Proposing…" : "Propose Trade"}
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          {result && (
            <span style={{ color: result.ok ? "#1B6F43" : "#A1192A", fontWeight: 700 }}>{result.msg}</span>
          )}
        </div>
      </Td>
    </tr>
  );
};

const TradeBlockPage = () => {
  const block = useTradeBlock();
  const league = useLeague();
  const userTeamId = league.data?.user_team_id ?? null;
  const [openFor, setOpenFor] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<"all" | PlayerKind>("all");

  const rows = useMemo(() => {
    const all = block.data ?? [];
    if (typeFilter === "all") return all;
    return all.filter((e) => e.player_type === typeFilter);
  }, [block.data, typeFilter]);

  return (
    <Shell crumbs={["Continental Hockey League", "Trade Block"]}>
      <div className="section-h">
        <h1>Trade Block</h1>
        <span className="sub">Players AI teams have made available</span>
      </div>

      <div className="card" style={{ padding: "12px 16px", marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <Button variant={typeFilter === "all" ? "primary" : "default"} onClick={() => setTypeFilter("all")}>
            All
          </Button>
          <Button
            variant={typeFilter === "skater" ? "primary" : "default"}
            onClick={() => setTypeFilter("skater")}
          >
            Skaters
          </Button>
          <Button
            variant={typeFilter === "goalie" ? "primary" : "default"}
            onClick={() => setTypeFilter("goalie")}
          >
            Goalies
          </Button>
        </div>
        {userTeamId == null && (
          <div style={{ marginTop: 12, color: "var(--ink-3)" }}>Set a user team to propose trades.</div>
        )}
      </div>

      <div className="card">
        <div className="ribbon-h">
          <span className="accent" />
          Available · {rows.length}
        </div>
        <Table>
          <thead>
            <tr>
              <Th>Team</Th>
              <Th>Player</Th>
              <Th>Pos</Th>
              <Th className="num">Age</Th>
              <Th className="num">OVR</Th>
              <Th className="num">Asking</Th>
              <Th>Reason</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => {
              const key = `${e.player_type}:${e.player_id}`;
              const open = openFor === key;
              return (
                <>
                  <tr key={key}>
                    <Td style={{ fontWeight: 700 }}>{e.team_abbreviation}</Td>
                    <Td>{e.name}</Td>
                    <Td style={{ color: "var(--ink-3)" }}>{e.position ?? "G"}</Td>
                    <Td className="num">{e.age}</Td>
                    <Td className="num">
                      <span className={`chip ovr ${attrClass(e.ovr)}`}>{e.ovr}</span>
                    </Td>
                    <Td className="num">{e.asking_value}</Td>
                    <Td style={{ color: "var(--ink-3)" }}>{e.reason}</Td>
                    <Td>
                      <Button
                        disabled={userTeamId == null}
                        onClick={() => setOpenFor(open ? null : key)}
                      >
                        {open ? "Close" : "Make Offer"}
                      </Button>
                    </Td>
                  </tr>
                  {open && userTeamId != null && (
                    <TradeOfferPanel
                      key={`${key}-panel`}
                      entry={e}
                      userTeamId={userTeamId}
                      onClose={() => setOpenFor(null)}
                    />
                  )}
                </>
              );
            })}
          </tbody>
        </Table>
      </div>
    </Shell>
  );
};

export const Route = createFileRoute("/trade-block")({ component: TradeBlockPage });
