import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Pagination, usePager } from "../components/Pagination";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { attrClass } from "../lib/team-colors";
import { useGoalieCareer, useGoalieDevelopment } from "../queries/development";
import { useGoalieDetail } from "../queries/stats";
import { useTeams } from "../queries/teams";

const dec3 = (v: number) => (v ? v.toFixed(3).replace(/^0/, "") : "—");

const GoalieDetailPage = () => {
  const { id } = Route.useParams();
  const q = useGoalieDetail(Number(id));
  const teams = useTeams();
  const nav = useNavigate();
  const pager = usePager(q.data?.game_log ?? []);
  const dev = useGoalieDevelopment(Number(id));
  const career = useGoalieCareer(Number(id));
  if (!q.data || !teams.data) {
    return <Shell crumbs={["Continental Hockey League", "Stats", "Goalie"]}>Loading…</Shell>;
  }
  const p = q.data;
  const team = teams.data.find((t) => t.id === p.team_id);
  const ovr = Math.round(
    0.3 * p.attributes.reflexes +
      0.25 * p.attributes.positioning +
      0.2 * p.attributes.rebound_control +
      0.15 * p.attributes.puck_handling +
      0.1 * p.attributes.mental,
  );

  return (
    <Shell crumbs={["Continental Hockey League", "Stats", p.name]}>
      <div className="section-h">
        <h1>{p.name}</h1>
        <span className="sub">
          Goaltender · Age {p.age} · {team?.name ?? "—"}
        </span>
        <div style={{ flex: 1 }} />
        <Link to="/stats" className="btn btn-ghost">
          ← All stats
        </Link>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 14, marginBottom: 14 }}>
        <Card title="Attributes" sub={`${ovr} OVR / ${p.potential} POT · ${p.development_type}`}>
          <div style={{ padding: "14px 16px", display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10 }}>
            {([
              ["OVR", ovr],
              ["RX", p.attributes.reflexes],
              ["PO", p.attributes.positioning],
              ["RC", p.attributes.rebound_control],
              ["PH", p.attributes.puck_handling],
              ["ME", p.attributes.mental],
            ] as [string, number][]).map(([k, v]) => (
              <div key={k} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span className="k" style={{ fontSize: 10, color: "var(--ink-4)", letterSpacing: "0.10em", textTransform: "uppercase" }}>
                  {k}
                </span>
                <span className={`chip ${attrClass(v)}`} style={{ fontSize: 16, padding: "4px 8px" }}>
                  {v}
                </span>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Season Totals">
          <div style={{ padding: "14px 16px", display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px 16px" }}>
            <Stat k="GP" v={String(p.totals.games_played)} />
            <Stat k="SA" v={String(p.totals.shots_against)} />
            <Stat k="SV" v={String(p.totals.saves)} />
            <Stat k="GA" v={String(p.totals.goals_against)} />
            <Stat k="SV%" v={dec3(p.totals.save_pct)} highlight />
            <Stat k="GAA" v={p.totals.gaa.toFixed(2)} />
          </div>
        </Card>
      </div>

      <Card title="Game Log" sub={`${p.game_log.length} games`}>
        <Table>
          <thead>
            <tr>
              <Th className="num">MD</Th>
              <Th></Th>
              <Th>Opponent</Th>
              <Th className="num">SA</Th>
              <Th className="num">SV</Th>
              <Th className="num">GA</Th>
              <Th className="num">SV%</Th>
            </tr>
          </thead>
          <tbody>
            {p.game_log.length === 0 && (
              <tr>
                <Td colSpan={7} style={{ textAlign: "center", color: "var(--ink-3)", padding: 16 }}>
                  No games played yet.
                </Td>
              </tr>
            )}
            {pager.slice.map((row) => (
              <tr
                key={row.game_id}
                style={{ cursor: "pointer" }}
                onClick={() => nav({ to: "/game/$gameId", params: { gameId: String(row.game_id) } })}
              >
                <Td className="num">{row.matchday}</Td>
                <Td style={{ color: "var(--ink-4)", fontSize: 11, fontWeight: 700, letterSpacing: "0.10em" }}>
                  {row.is_home ? "VS" : "@"}
                </Td>
                <Td>
                  <span className="team-row">
                    <Logo teamId={row.opponent_team_id} size={18} />
                    <span className="nm">{teams.data!.find((t) => t.id === row.opponent_team_id)?.name ?? "—"}</span>
                  </span>
                </Td>
                <Td className="num">{row.shots_against}</Td>
                <Td className="num">{row.saves}</Td>
                <Td className="num">{row.goals_against}</Td>
                <Td className="num">
                  <b>{dec3(row.save_pct)}</b>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
        <Pagination {...pager} onPage={pager.setPage} />
      </Card>

      {career.data && career.data.by_season.length > 0 && (
        <Card title="Career">
          <Table>
            <thead>
              <tr>
                <Th>Season</Th>
                <Th className="num">GP</Th>
                <Th className="num">SA</Th>
                <Th className="num">SV</Th>
                <Th className="num">GA</Th>
                <Th className="num">SV%</Th>
              </tr>
            </thead>
            <tbody>
              {career.data.by_season.map((row) => (
                <tr key={row.season_id}>
                  <Td>{row.season_id}</Td>
                  <Td className="num">{row.gp}</Td>
                  <Td className="num">{row.shots_against}</Td>
                  <Td className="num">{row.saves}</Td>
                  <Td className="num">{row.goals_against}</Td>
                  <Td className="num"><b>{dec3(row.sv_pct)}</b></Td>
                </tr>
              ))}
              <tr style={{ fontWeight: 700, borderTop: "2px solid var(--line)" }}>
                <Td>Total</Td>
                <Td className="num">{career.data.totals.gp}</Td>
                <Td className="num">{career.data.totals.shots_against}</Td>
                <Td className="num">{career.data.totals.saves}</Td>
                <Td className="num">{career.data.totals.goals_against}</Td>
                <Td className="num">{dec3(career.data.totals.sv_pct)}</Td>
              </tr>
            </tbody>
          </Table>
        </Card>
      )}

      {dev.data && dev.data.history.length > 0 && (
        <Card title="Development History" sub={`${dev.data.history.length} season(s)`}>
          <div>
            {dev.data.history.map((sp) => {
              const arrow = sp.overall_after === sp.overall_before ? "→" : sp.overall_after > sp.overall_before ? "↑" : "↓";
              return (
                <div key={`${sp.age_before}-${sp.age_after}`} style={{ padding: "10px 14px", borderBottom: "1px solid var(--line)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Age {sp.age_before} → {sp.age_after}</span>
                    <span style={{ fontFamily: "'Roboto Condensed', monospace" }}>
                      OVR {sp.overall_before} {arrow} {sp.overall_after}{" "}
                      <span style={{ color: "var(--ink-3)", fontStyle: "italic" }}>({sp.summary_reason})</span>
                    </span>
                  </div>
                  {sp.events.length > 0 && (
                    <div style={{ marginTop: 4, fontSize: 12, color: "var(--ink-2)", display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 4 }}>
                      {sp.events.map((e, i) => (
                        <span key={i}>
                          {e.attribute}: {e.old_value} → {e.new_value} ({e.delta > 0 ? "+" : ""}{e.delta})
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </Shell>
  );
};

const Stat = ({ k, v, highlight = false }: { k: string; v: string; highlight?: boolean }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
    <span style={{ fontSize: 10, color: "var(--ink-4)", letterSpacing: "0.10em", textTransform: "uppercase" }}>
      {k}
    </span>
    <span
      style={{
        font: "700 22px/1 'Roboto Condensed', monospace",
        color: highlight ? "var(--gold)" : "var(--ink)",
      }}
    >
      {v}
    </span>
  </div>
);

export const Route = createFileRoute("/player/goalie/$id")({ component: GoalieDetailPage });
