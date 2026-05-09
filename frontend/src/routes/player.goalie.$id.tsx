import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { ContractBadge } from "../components/ContractBadge";
import { Logo } from "../components/Logo";
import { Pagination, usePager } from "../components/Pagination";
import { PlayerSilhouette } from "../components/PlayerSilhouette";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { attrClass } from "../lib/team-colors";
import { goalieSnapshot, goalieStrengths, goalieWeaknesses } from "../lib/player-narrative";
import { useLeague } from "../queries/league";
import { useGoalieCareer, useGoalieDevelopment } from "../queries/development";
import { useReleaseGoalie } from "../queries/free-agents";
import { useGoalieDetail } from "../queries/stats";
import { useTeams } from "../queries/teams";

const dec3 = (v: number) => (v ? v.toFixed(3).replace(/^0/, "") : "—");
const fixed2 = (v: number) => (Number.isFinite(v) ? v.toFixed(2) : "—");

const GoalieDetailPage = () => {
  const { id } = Route.useParams();
  const gid = Number(id);
  const q = useGoalieDetail(gid);
  const teams = useTeams();
  const league = useLeague();
  const nav = useNavigate();
  const pager = usePager(q.data?.game_log ?? []);
  const dev = useGoalieDevelopment(gid);
  const career = useGoalieCareer(gid);
  const releaseGoalie = useReleaseGoalie(q.data?.team_id ?? 0);

  if (!q.data || !teams.data) {
    return <Shell crumbs={["Continental Hockey League", "Players", "Goalie"]}>Loading…</Shell>;
  }
  const p = q.data;
  const team = teams.data.find((t) => t.id === p.team_id);
  const isUserPlayer = league.data?.user_team_id === p.team_id;
  const ovr = Math.round(
    0.3 * p.attributes.reflexes +
      0.25 * p.attributes.positioning +
      0.2 * p.attributes.rebound_control +
      0.15 * p.attributes.puck_handling +
      0.1 * p.attributes.mental,
  );
  const gp = p.totals.games_played || 0;
  const last5 = p.game_log.slice(-5);
  const last5Sum = last5.reduce(
    (a, r) => ({
      sa: a.sa + r.shots_against,
      sv: a.sv + r.saves,
      ga: a.ga + r.goals_against,
    }),
    { sa: 0, sv: 0, ga: 0 },
  );
  const last5Pct = last5Sum.sa ? last5Sum.sv / last5Sum.sa : 0;

  const onRelease = () => {
    if (window.confirm(`Release ${p.name}? They'll become a free agent.`)) {
      releaseGoalie.mutate(p.id, {
        onSuccess: () => nav({ to: "/free-agents" }),
      });
    }
  };

  return (
    <Shell crumbs={["Continental Hockey League", "Players", p.name]}>
      <div className="player-hero">
        <PlayerSilhouette teamId={p.team_id} size={104} />
        <div className="player-hero-meta">
          <h1 className="player-hero-name">{p.name}</h1>
          <div className="player-hero-sub">
            <span>G</span>
            <span className="dot">·</span>
            <span>Age {p.age}</span>
            <span className="dot">·</span>
            <span className="team-row">
              {p.team_id != null && <Logo teamId={p.team_id} size={20} />}
              <span>{team?.name ?? "—"}</span>
            </span>
          </div>
          <div className="player-hero-chips">
            <span className={`chip ovr ${attrClass(ovr)}`}>{ovr} OVR</span>
            <span className={`chip ovr ${attrClass(p.potential)}`}>{p.potential} POT</span>
            <span className="tag tag-prospect">{p.development_type.replace(/_/g, " ")}</span>
            <ContractBadge contract={p.contract} currentYear={league.data?.year ?? 0} />
          </div>
          <div className="player-hero-totals">
            <HeroStat k="GP" v={String(gp)} />
            <HeroStat k="SA" v={String(p.totals.shots_against)} />
            <HeroStat k="SV" v={String(p.totals.saves)} />
            <HeroStat k="GA" v={String(p.totals.goals_against)} />
            <HeroStat k="SV%" v={dec3(p.totals.save_pct)} highlight />
            <HeroStat k="GAA" v={p.totals.gaa.toFixed(2)} />
          </div>
        </div>
        <div className="player-hero-actions">
          {isUserPlayer && (
            <Link to="/team/$teamId/lineup" params={{ teamId: String(p.team_id) }} className="btn btn-primary">
              Edit Lineup
            </Link>
          )}
          {isUserPlayer && (
            <Button variant="ghost" onClick={onRelease} disabled={releaseGoalie.isPending}>
              Release Player
            </Button>
          )}
          <Button variant="ghost" disabled title="Coming soon">
            Compare Player
          </Button>
        </div>
      </div>

      <div className="player-grid-4">
        <Card title="Player Snapshot">
          <div className="snapshot-body">
            <p>{goalieSnapshot(p, ovr)}</p>
          </div>
        </Card>

        <Card title="Attributes" sub={`${ovr} OVR`}>
          <div className="attr-bars">
            <AttrBar label="Reflexes" value={p.attributes.reflexes} kind="off" />
            <AttrBar label="Positioning" value={p.attributes.positioning} kind="def" />
            <AttrBar label="Rebound Ctrl" value={p.attributes.rebound_control} kind="def" />
            <AttrBar label="Puck Handling" value={p.attributes.puck_handling} kind="play" />
            <AttrBar label="Mental" value={p.attributes.mental} kind="play" />
          </div>
        </Card>

        <Card title="Season Production">
          <div className="prod-grid">
            <Stat k="GP" v={String(gp)} />
            <Stat k="Shots Against" v={String(p.totals.shots_against)} />
            <Stat k="Saves" v={String(p.totals.saves)} />
            <Stat k="Save %" v={dec3(p.totals.save_pct)} highlight />
            <Stat k="Goals Against" v={String(p.totals.goals_against)} />
            <Stat k="GAA" v={p.totals.gaa.toFixed(2)} />
          </div>
        </Card>

        <Card title="Rates / Pace">
          <div className="rates-grid">
            <div>
              <div className="rates-h">Per Game</div>
              <Stat k="SA / GP" v={fixed2(gp ? p.totals.shots_against / gp : 0)} />
              <Stat k="SV / GP" v={fixed2(gp ? p.totals.saves / gp : 0)} />
              <Stat k="GA / GP" v={fixed2(gp ? p.totals.goals_against / gp : 0)} />
              <Stat k="GAA" v={p.totals.gaa.toFixed(2)} />
            </div>
            <div>
              <div className="rates-h">82-Game Pace</div>
              <Stat k="SA" v={gp ? String(Math.round((p.totals.shots_against / gp) * 82)) : "—"} />
              <Stat k="SV" v={gp ? String(Math.round((p.totals.saves / gp) * 82)) : "—"} />
              <Stat k="GA" v={gp ? String(Math.round((p.totals.goals_against / gp) * 82)) : "—"} />
              <Stat k="SV%" v={dec3(p.totals.save_pct)} />
            </div>
          </div>
        </Card>
      </div>

      <div className="player-grid-3">
        <Card title="Lineup Status">
          <div className="lineup-status">
            {p.lineup_status.slot_label ? (
              <>
                <div className="ls-line">{p.lineup_status.slot_label}</div>
                <div className="ls-sub">Goaltender depth chart</div>
              </>
            ) : (
              <div className="ls-empty">Not in current lineup</div>
            )}
          </div>
        </Card>

        <Card title="Strengths">
          <ul className="bullet-list bullet-good">
            {goalieStrengths(p).map((s) => (
              <li key={s}>{s}</li>
            ))}
            {goalieStrengths(p).length === 0 && <li className="muted">No standout traits yet.</li>}
          </ul>
        </Card>

        <Card title="Weaknesses">
          <ul className="bullet-list bullet-bad">
            {goalieWeaknesses(p).map((s) => (
              <li key={s}>{s}</li>
            ))}
            {goalieWeaknesses(p).length === 0 && <li className="muted">No glaring weaknesses.</li>}
          </ul>
        </Card>
      </div>

      <Card
        title="Game Log"
        sub={`${p.game_log.length} games`}
        link={
          last5.length > 0 ? (
            <span style={{ fontSize: 12, color: "var(--ink-3)" }}>
              Last 5: <b style={{ color: "var(--ink)" }}>{last5Sum.sa} SA</b>{" "}
              <b style={{ color: "var(--ink)" }}>{last5Sum.sv} SV</b>{" "}
              <b style={{ color: "var(--ink)" }}>{last5Sum.ga} GA</b>{" "}
              <b style={{ color: "var(--ink)" }}>{dec3(last5Pct)} SV%</b>
            </span>
          ) : null
        }
      >
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
                  <Td className="num">
                    <b>{dec3(row.sv_pct)}</b>
                  </Td>
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
              const arrow =
                sp.overall_after === sp.overall_before
                  ? "→"
                  : sp.overall_after > sp.overall_before
                    ? "↑"
                    : "↓";
              return (
                <div
                  key={`${sp.age_before}-${sp.age_after}`}
                  style={{ padding: "10px 14px", borderBottom: "1px solid var(--line)" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>
                      Age {sp.age_before} → {sp.age_after}
                    </span>
                    <span style={{ fontFamily: "'Roboto Condensed', monospace" }}>
                      OVR {sp.overall_before} {arrow} {sp.overall_after}{" "}
                      <span style={{ color: "var(--ink-3)", fontStyle: "italic" }}>({sp.summary_reason})</span>
                    </span>
                  </div>
                  {sp.events.length > 0 && (
                    <div
                      style={{
                        marginTop: 4,
                        fontSize: 12,
                        color: "var(--ink-2)",
                        display: "grid",
                        gridTemplateColumns: "repeat(3, 1fr)",
                        gap: 4,
                      }}
                    >
                      {sp.events.map((e, i) => (
                        <span key={i}>
                          {e.attribute}: {e.old_value} → {e.new_value} ({e.delta > 0 ? "+" : ""}
                          {e.delta})
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

const HeroStat = ({ k, v, highlight = false }: { k: string; v: string; highlight?: boolean }) => (
  <div className="hero-stat">
    <span className="hero-stat-v" style={highlight ? { color: "#A1192A" } : undefined}>
      {v}
    </span>
    <span className="hero-stat-k">{k}</span>
  </div>
);

const Stat = ({ k, v, highlight = false }: { k: string; v: string; highlight?: boolean }) => (
  <div className="stat-pair">
    <span className="stat-k">{k}</span>
    <span className="stat-v" style={highlight ? { color: "#A1192A" } : undefined}>
      {v}
    </span>
  </div>
);

const AttrBar = ({
  label,
  value,
  kind,
}: {
  label: string;
  value: number;
  kind: "off" | "play" | "def";
}) => {
  const color = kind === "off" ? "#1B6F43" : kind === "def" ? "#A1192A" : "#1E3A8A";
  const pct = Math.max(2, Math.min(100, value));
  return (
    <div className="attr-bar">
      <span className="attr-bar-label">{label}</span>
      <div className="attr-bar-track">
        <div className="attr-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="attr-bar-value">{value}</span>
    </div>
  );
};

export const Route = createFileRoute("/player/goalie/$id")({ component: GoalieDetailPage });
