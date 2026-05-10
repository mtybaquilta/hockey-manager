import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";

import { Button } from "../components/Button";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { skaterOvr } from "../lib/roster-tags";
import { attrClass } from "../lib/team-colors";
import type {
  PlayerKind,
  TradeEvaluateResponse,
  TradeExecuteResponse,
  TradeOfferPlayer,
} from "../api/types";
import { useLeague } from "../queries/league";
import { useTeams, useRoster } from "../queries/teams";
import { useEvaluateTrade, useExecuteTrade } from "../queries/trades";

const goalieOvr = (g: { reflexes: number; positioning: number; rebound_control: number; puck_handling: number; mental: number }) =>
  Math.round(0.3 * g.reflexes + 0.25 * g.positioning + 0.2 * g.rebound_control + 0.15 * g.puck_handling + 0.1 * g.mental);

const SidePicker = ({
  title,
  roster,
  selected,
  onAdd,
  onRemove,
}: {
  title: string;
  roster: ReturnType<typeof useRoster>;
  selected: TradeOfferPlayer[];
  onAdd: (p: TradeOfferPlayer) => void;
  onRemove: (p: TradeOfferPlayer) => void;
}) => {
  const isSelected = (kind: PlayerKind, id: number) =>
    selected.some((s) => s.player_type === kind && s.player_id === id);

  return (
    <div className="card" style={{ padding: 12, minWidth: 320, flex: 1 }}>
      <div className="ribbon-h"><span className="accent" />{title} ({selected.length}/3)</div>
      {!roster.data ? (
        <div style={{ padding: 12, color: "var(--ink-3)" }}>Loading…</div>
      ) : (
        <Table>
          <thead>
            <tr><Th>Name</Th><Th>Pos</Th><Th className="num">OVR</Th><Th /></tr>
          </thead>
          <tbody>
            {roster.data.skaters.map((s) => {
              const sel = isSelected("skater", s.id);
              const ovr = skaterOvr(s);
              return (
                <tr key={`s${s.id}`}>
                  <Td>{s.name}</Td>
                  <Td style={{ color: "var(--ink-3)" }}>{s.position}</Td>
                  <Td className="num"><span className={`chip ovr ${attrClass(ovr)}`}>{ovr}</span></Td>
                  <Td>
                    <Button
                      variant={sel ? "ghost" : "default"}
                      disabled={!sel && selected.length >= 3}
                      onClick={() => sel
                        ? onRemove({ player_type: "skater", player_id: s.id })
                        : onAdd({ player_type: "skater", player_id: s.id })}
                    >
                      {sel ? "Remove" : "Add"}
                    </Button>
                  </Td>
                </tr>
              );
            })}
            {roster.data.goalies.map((g) => {
              const sel = isSelected("goalie", g.id);
              const ovr = goalieOvr(g);
              return (
                <tr key={`g${g.id}`}>
                  <Td>{g.name}</Td>
                  <Td style={{ color: "var(--ink-3)" }}>G</Td>
                  <Td className="num"><span className={`chip ovr ${attrClass(ovr)}`}>{ovr}</span></Td>
                  <Td>
                    <Button
                      variant={sel ? "ghost" : "default"}
                      disabled={!sel && selected.length >= 3}
                      onClick={() => sel
                        ? onRemove({ player_type: "goalie", player_id: g.id })
                        : onAdd({ player_type: "goalie", player_id: g.id })}
                    >
                      {sel ? "Remove" : "Add"}
                    </Button>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </div>
  );
};

const OutlookBadge = ({ outlook }: { outlook: "accept" | "close" | "reject" }) => {
  const color = outlook === "accept" ? "#1B6F43" : outlook === "close" ? "#A57400" : "#A1192A";
  const label = outlook === "accept" ? "Will accept" : outlook === "close" ? "Close" : "Will reject";
  return <span style={{ color, fontWeight: 700 }}>{label}</span>;
};

const TradesPage = () => {
  const league = useLeague();
  const teams = useTeams();
  const userTeamId = league.data?.user_team_id ?? null;
  const aiTeams = useMemo(
    () => (teams.data ?? []).filter((t) => t.id !== userTeamId),
    [teams.data, userTeamId],
  );
  const [partnerId, setPartnerId] = useState<number | null>(null);
  useEffect(() => {
    if (partnerId == null && aiTeams.length > 0) setPartnerId(aiTeams[0].id);
  }, [aiTeams, partnerId]);

  const userRoster = useRoster(userTeamId ?? 0);
  const partnerRoster = useRoster(partnerId ?? 0);

  const [offered, setOffered] = useState<TradeOfferPlayer[]>([]);
  const [requested, setRequested] = useState<TradeOfferPlayer[]>([]);
  const [outlook, setOutlook] = useState<TradeEvaluateResponse | null>(null);
  const [submitMsg, setSubmitMsg] = useState<string | null>(null);

  const evalMut = useEvaluateTrade();
  const execMut = useExecuteTrade(userTeamId, partnerId);

  const resetSelections = () => {
    setOffered([]);
    setRequested([]);
    setOutlook(null);
    setSubmitMsg(null);
  };

  useEffect(() => { resetSelections(); }, [partnerId]);

  useEffect(() => {
    setSubmitMsg(null);
    if (userTeamId == null || partnerId == null || offered.length === 0 || requested.length === 0) {
      setOutlook(null);
      return;
    }
    evalMut.mutate(
      { partner_team_id: partnerId, offered, requested },
      { onSuccess: (res) => setOutlook(res), onError: () => setOutlook(null) },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(offered), JSON.stringify(requested), partnerId, userTeamId]);

  const submit = () => {
    if (userTeamId == null || partnerId == null) return;
    setSubmitMsg(null);
    execMut.mutate(
      { partner_team_id: partnerId, offered, requested },
      {
        onSuccess: (res: TradeExecuteResponse) => {
          if (res.accepted) {
            setSubmitMsg(`Trade accepted. Acquired ${res.acquired.length} player(s).`);
            resetSelections();
          } else {
            setSubmitMsg("Trade rejected.");
            setOutlook(res);
          }
        },
        onError: (err: unknown) => {
          const m = err instanceof Error ? err.message : "Trade failed.";
          setSubmitMsg(m);
        },
      },
    );
  };

  if (userTeamId == null) {
    return <Shell crumbs={["Trades"]}><div className="card" style={{ padding: 16 }}>Choose a team first.</div></Shell>;
  }

  return (
    <Shell crumbs={["Continental Hockey League", "Trades"]}>
      <div className="section-h">
        <h1>Trades</h1>
        <span className="sub">Build an offer (1–3 vs 1–3) and see how the partner reacts</span>
      </div>

      <div className="card" style={{ padding: 12, marginBottom: 14 }}>
        <label style={{ marginRight: 8, fontWeight: 600 }}>Trade partner:</label>
        <select value={partnerId ?? ""} onChange={(e) => setPartnerId(e.target.value ? Number(e.target.value) : null)}>
          {aiTeams.map((t) => (
            <option key={t.id} value={t.id}>{t.name} ({t.abbreviation})</option>
          ))}
        </select>
      </div>

      <div style={{ display: "flex", gap: 14, alignItems: "stretch", flexWrap: "wrap" }}>
        <SidePicker
          title="You give"
          roster={userRoster}
          selected={offered}
          onAdd={(p) => setOffered((s) => [...s, p])}
          onRemove={(p) => setOffered((s) => s.filter((x) => !(x.player_type === p.player_type && x.player_id === p.player_id)))}
        />
        <SidePicker
          title="You get"
          roster={partnerRoster}
          selected={requested}
          onAdd={(p) => setRequested((s) => [...s, p])}
          onRemove={(p) => setRequested((s) => s.filter((x) => !(x.player_type === p.player_type && x.player_id === p.player_id)))}
        />
      </div>

      <div className="card" style={{ padding: 12, marginTop: 14 }}>
        <div className="ribbon-h"><span className="accent" />Outlook</div>
        {!outlook ? (
          <div style={{ padding: 12, color: "var(--ink-3)" }}>
            {evalMut.isPending ? "Evaluating…" : "Add at least one player to each side to see the outlook."}
          </div>
        ) : (
          <div style={{ padding: 12 }}>
            <div style={{ marginBottom: 8 }}>
              <OutlookBadge outlook={outlook.outlook} />
              <span style={{ marginLeft: 12, color: "var(--ink-3)" }}>
                offered value <b>{outlook.offered_value}</b> · requested value <b>{outlook.requested_value}</b>
              </span>
            </div>
            {outlook.rejection_reasons.length > 0 && (
              <ul style={{ marginTop: 4 }}>
                {outlook.rejection_reasons.map((r, i) => (
                  <li key={i} style={{ color: "#A1192A" }}>{r.code}: {r.message}</li>
                ))}
              </ul>
            )}
            {outlook.warnings.length > 0 && (
              <ul style={{ marginTop: 4 }}>
                {outlook.warnings.map((w, i) => (
                  <li key={i} style={{ color: "#A57400" }}>{w.message}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        <div style={{ display: "flex", gap: 8, padding: 12 }}>
          <Button
            variant="primary"
            disabled={!outlook?.accepted || execMut.isPending}
            onClick={submit}
          >
            {execMut.isPending ? "Submitting…" : "Submit Trade"}
          </Button>
          <Button variant="ghost" onClick={resetSelections}>Clear</Button>
          {submitMsg && <span style={{ alignSelf: "center", fontWeight: 700 }}>{submitMsg}</span>}
        </div>
      </div>
    </Shell>
  );
};

export const Route = createFileRoute("/trades")({ component: TradesPage });
