import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Pagination, usePager } from "../components/Pagination";
import { PlayerSilhouette } from "../components/PlayerSilhouette";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { attrClass } from "../lib/team-colors";
import { skaterSnapshot, skaterStrengths, skaterWeaknesses } from "../lib/player-narrative";
import { useLeague } from "../queries/league";
import { useSkaterCareer, useSkaterDevelopment } from "../queries/development";
import { useReleaseSkater } from "../queries/free-agents";
import { useSkaterDetail } from "../queries/stats";
import { useTeams } from "../queries/teams";

const pct = (v: number) => (v ? `${(v * 100).toFixed(1)}%` : "—");
const fixed2 = (v: number) => (Number.isFinite(v) ? v.toFixed(2) : "—");

const SkaterDetailPage = () => {
  const { id } = Route.useParams();
  const sid = Number(id);
  const q = useSkaterDetail(sid);
  const teams = useTeams();
  const league = useLeague();
  const nav = useNavigate();
  const pager = usePager(q.data?.game_log ?? []);
  const dev = useSkaterDevelopment(sid);
  const career = useSkaterCareer(sid);
  const releaseSkater = useReleaseSkater(q.data?.team_id ?? 0);

  if (!q.data || !teams.data) {
    return <Shell crumbs={["Continental Hockey League", "Players", "Player"]}>Loading…</Shell>;
  }
  const p = q.data;
  const team = teams.data.find((t) => t.id === p.team_id);
  const isUserPlayer = league.data?.user_team_id === p.team_id;
  const ovr = Math.round(
    0.25 * p.attributes.shooting +
      0.2 * p.attributes.passing +
      0.2 * p.attributes.skating +
      0.2 * p.attributes.defense +
      0.15 * p.attributes.physical,
  );
  const gp = p.totals.games_played || 0;
  const last5 = p.game_log.slice(-5);
  const last5Sum = last5.reduce(
    (a, r) => ({
      g: a.g + r.goals,
      a: a.a + r.assists,
      pts: a.pts + r.points,
      sog: a.sog + r.shots,
    }),
    { g: 0, a: 0, pts: 0, sog: 0 },
  );
  const seasonPace82 = (per: number) => Math.round(per * 82);

  const onRelease = () => {
    if (window.confirm(`Release ${p.name}? They'll become a free agent.`)) {
      releaseSkater.mutate(p.id, {
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
            <span>{p.position}</span>
            <span className="dot">·</span>
            <span>Age {p.age}</span>
            <span className="dot">·</span>
            <span className="team-row">
              <Logo teamId={p.team_id} size={20} />
              <span>{team?.name ?? "—"}</span>
            </span>
          </div>
          <div className="player-hero-chips">
            <span className={`chip ovr ${attrClass(ovr)}`}>{ovr} OVR</span>
            <span className={`chip ovr ${attrClass(p.potential)}`}>{p.potential} POT</span>
            <span className="tag tag-prospect">{p.development_type.replace(/_/g, " ")}</span>
          </div>
          <div className="player-hero-totals">
            <HeroStat k="GP" v={String(gp)} />
            <HeroStat k="G" v={String(p.totals.goals)} />
            <HeroStat k="A" v={String(p.totals.assists)} />
            <HeroStat k="PTS" v={String(p.totals.points)} highlight />
            <HeroStat k="SOG" v={String(p.totals.shots)} />
            <HeroStat k="SH%" v={pct(p.totals.shooting_pct)} />
          </div>
        </div>
        <div className="player-hero-actions">
          {isUserPlayer && (
            <Link to="/team/$teamId/lineup" params={{ teamId: String(p.team_id) }} className="btn btn-primary">
              Edit Lineup
            </Link>
          )}
          {isUserPlayer && (
            <Button variant="ghost" onClick={onRelease} disabled={releaseSkater.isPending}>
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
            <p>{skaterSnapshot(p, ovr)}</p>
          </div>
        </Card>

        <Card title="Attributes" sub={`${ovr} OVR`}>
          <div className="attr-bars">
            <AttrBar label="Skating" value={p.attributes.skating} kind="off" />
            <AttrBar label="Shooting" value={p.attributes.shooting} kind="off" />
            <AttrBar label="Passing" value={p.attributes.passing} kind="play" />
            <AttrBar label="Defense" value={p.attributes.defense} kind="def" />
            <AttrBar label="Physical" value={p.attributes.physical} kind="play" />
          </div>
        </Card>

        <Card title="Season Production">
          <div className="prod-grid">
            <Stat k="GP" v={String(gp)} />
            <Stat k="Shots on Goal" v={String(p.totals.shots)} />
            <Stat k="Goals" v={String(p.totals.goals)} />
            <Stat k="Shooting %" v={pct(p.totals.shooting_pct)} />
            <Stat k="Assists" v={String(p.totals.assists)} />
            <Stat k="Points" v={String(p.totals.points)} highlight />
          </div>
        </Card>

        <Card title="Rates / Pace">
          <div className="rates-grid">
            <div>
              <div className="rates-h">Per Game</div>
              <Stat k="Points / GP" v={fixed2(gp ? p.totals.points / gp : 0)} />
              <Stat k="Goals / GP" v={fixed2(gp ? p.totals.goals / gp : 0)} />
              <Stat k="Assists / GP" v={fixed2(gp ? p.totals.assists / gp : 0)} />
              <Stat k="SOG / GP" v={fixed2(gp ? p.totals.shots / gp : 0)} />
            </div>
            <div>
              <div className="rates-h">82-Game Pace</div>
              <Stat k="Goals" v={gp ? String(seasonPace82(p.totals.goals / gp)) : "—"} />
              <Stat k="Assists" v={gp ? String(seasonPace82(p.totals.assists / gp)) : "—"} />
              <Stat k="Points" v={gp ? String(seasonPace82(p.totals.points / gp)) : "—"} />
              <Stat k="SOG" v={gp ? String(seasonPace82(p.totals.shots / gp)) : "—"} />
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
                <div className="ls-sub">5v5 assignment</div>
                {p.lineup_status.special_teams.length > 0 && (
                  <div className="ls-st">
                    Special teams:{" "}
                    {p.lineup_status.special_teams.map((u) => (
                      <span key={u} className="tag tag-top" style={{ marginLeft: 4 }}>
                        {u}
                      </span>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="ls-empty">Not in current lineup</div>
            )}
          </div>
        </Card>

        <Card title="Strengths">
          <ul className="bullet-list bullet-good">
            {skaterStrengths(p).map((s) => (
              <li key={s}>{s}</li>
            ))}
            {skaterStrengths(p).length === 0 && <li className="muted">No standout traits yet.</li>}
          </ul>
        </Card>

        <Card title="Weaknesses">
          <ul className="bullet-list bullet-bad">
            {skaterWeaknesses(p).map((s) => (
              <li key={s}>{s}</li>
            ))}
            {skaterWeaknesses(p).length === 0 && <li className="muted">No glaring weaknesses.</li>}
          </ul>
        </Card>
      </div>

      <Card
        title="Game Log"
        sub={`${p.game_log.length} games`}
        link={
          last5.length > 0 ? (
            <span style={{ fontSize: 12, color: "var(--ink-3)" }}>
              Last 5: <b style={{ color: "var(--ink)" }}>{last5Sum.g} G</b>{" "}
              <b style={{ color: "var(--ink)" }}>{last5Sum.a} A</b>{" "}
              <b style={{ color: "var(--ink)" }}>{last5Sum.pts} PTS</b>{" "}
              <b style={{ color: "var(--ink)" }}>{last5Sum.sog} SOG</b>
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
              <Th className="num">G</Th>
              <Th className="num">A</Th>
              <Th className="num">PTS</Th>
              <Th className="num">SOG</Th>
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
                <Td className="num">{row.goals}</Td>
                <Td className="num">{row.assists}</Td>
                <Td className="num">
                  <b>{row.points}</b>
                </Td>
                <Td className="num">{row.shots}</Td>
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
                <Th className="num">G</Th>
                <Th className="num">A</Th>
                <Th className="num">PTS</Th>
                <Th className="num">SOG</Th>
              </tr>
            </thead>
            <tbody>
              {career.data.by_season.map((row) => (
                <tr key={row.season_id}>
                  <Td>{row.season_id}</Td>
                  <Td className="num">{row.gp}</Td>
                  <Td className="num">{row.g}</Td>
                  <Td className="num">{row.a}</Td>
                  <Td className="num">
                    <b>{row.pts}</b>
                  </Td>
                  <Td className="num">{row.sog}</Td>
                </tr>
              ))}
              <tr style={{ fontWeight: 700, borderTop: "2px solid var(--line)" }}>
                <Td>Total</Td>
                <Td className="num">{career.data.totals.gp}</Td>
                <Td className="num">{career.data.totals.g}</Td>
                <Td className="num">{career.data.totals.a}</Td>
                <Td className="num">{career.data.totals.pts}</Td>
                <Td className="num">{career.data.totals.sog}</Td>
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

export const Route = createFileRoute("/player/skater/$id")({ component: SkaterDetailPage });
