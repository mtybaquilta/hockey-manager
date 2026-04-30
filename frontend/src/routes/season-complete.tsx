import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { useStartNextSeason } from "../queries/development";
import { useCreateLeague } from "../queries/league";
import { useSeasonStats } from "../queries/season";
import { useStandings } from "../queries/standings";
import { useTeams } from "../queries/teams";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const num = (v: number) => v.toFixed(2);

const Done = () => {
  const s = useStandings();
  const stats = useSeasonStats();
  const teams = useTeams();
  const create = useCreateLeague();
  const startNext = useStartNextSeason();
  const navigate = useNavigate();
  if (!s.data || !stats.data || !teams.data) {
    return <Shell crumbs={["Continental Hockey League", "Season Complete"]}>Loading…</Shell>;
  }
  const champ = s.data.rows[0];
  const champTeam = teams.data.find((t) => t.id === champ.team_id);
  const st = stats.data;

  return (
    <Shell
      crumbs={["Continental Hockey League", "Season Complete"]}
      topRight={
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn btn-primary"
            disabled={startNext.isPending}
            onClick={() =>
              startNext.mutate(undefined, {
                onSuccess: (res) => {
                  navigate({ to: "/development-summary", search: { season_id: res.new_season_id } });
                },
              })
            }
          >
            {startNext.isPending ? "Starting…" : "Start Next Season"}
          </button>
          <button className="btn" disabled={create.isPending} onClick={() => create.mutate(undefined)}>
            {create.isPending ? "Resetting…" : "New League"}
          </button>
        </div>
      }
    >
      {/* Champion banner */}
      <div
        style={{
          background: "linear-gradient(110deg, var(--navy-800) 0%, var(--navy-700) 60%, var(--navy-600) 100%)",
          color: "#fff",
          borderRadius: 8,
          padding: "28px 32px",
          marginBottom: 18,
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            right: -40,
            top: -40,
            width: 280,
            height: 280,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(220,38,38,.20) 0%, transparent 70%)",
          }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          {champTeam && <Logo teamId={champTeam.id} size={72} />}
          <div>
            <div style={{ fontSize: 11, letterSpacing: "0.18em", color: "rgba(255,255,255,.6)", textTransform: "uppercase", fontWeight: 700 }}>
              Champion · '25-26
            </div>
            <div style={{ fontSize: 38, fontWeight: 700, letterSpacing: "-0.02em", marginTop: 2 }}>
              {champTeam?.name ?? "—"}
            </div>
            <div style={{ fontFamily: "'Roboto Condensed', monospace", fontSize: 16, marginTop: 6 }}>
              {champ.points} PTS · {champ.wins}-{champ.losses}-{champ.ot_losses}
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginBottom: 14 }}>
        <div className="k-stat">
          <div className="lbl">Goals / Game</div>
          <div className="val">{num(st.avg_total_goals_per_game)}</div>
          <div className="delta">{num(st.avg_total_shots_per_game)} shots/game</div>
        </div>
        <div className="k-stat">
          <div className="lbl">League SV%</div>
          <div className="val">{pct(st.league_save_percentage)}</div>
          <div className="delta">SH% {pct(st.league_shooting_percentage)}</div>
        </div>
        <div className="k-stat">
          <div className="lbl">Home Win%</div>
          <div className="val">{pct(st.home_win_pct)}</div>
          <div className="delta">
            OT {pct(st.overtime_pct)} · SO {pct(st.shootout_pct)}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
        <Card title="Top Scorer">
          {st.top_scorer_name ? (
            <div style={{ padding: "16px 18px" }}>
              <div style={{ fontSize: 22, fontWeight: 700 }}>{st.top_scorer_name}</div>
              <div style={{ fontFamily: "'Roboto Condensed', monospace", fontSize: 28, fontWeight: 700, color: "var(--gold)", marginTop: 4 }}>
                {st.top_scorer_points}
                <span style={{ fontSize: 14, color: "var(--ink-3)", marginLeft: 6 }}>PTS</span>
              </div>
              <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 6 }}>
                {st.top_scorer_goals}G · {st.top_scorer_assists}A
              </div>
            </div>
          ) : (
            <div style={{ padding: 20, color: "var(--ink-3)" }}>—</div>
          )}
        </Card>
        <Card title="Top Goalie" sub="≥ 30 SA">
          {st.top_goalie_name ? (
            <div style={{ padding: "16px 18px" }}>
              <div style={{ fontSize: 22, fontWeight: 700 }}>{st.top_goalie_name}</div>
              <div style={{ fontFamily: "'Roboto Condensed', monospace", fontSize: 28, fontWeight: 700, color: "var(--gold)", marginTop: 4 }}>
                {pct(st.top_goalie_save_pct)}
                <span style={{ fontSize: 14, color: "var(--ink-3)", marginLeft: 6 }}>SV%</span>
              </div>
              <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 6 }}>
                on {st.top_goalie_shots_against} SA
              </div>
            </div>
          ) : (
            <div style={{ padding: 20, color: "var(--ink-3)" }}>—</div>
          )}
        </Card>
      </div>

      <Card title="Final Standings">
        <Table>
          <thead>
            <tr>
              <Th></Th>
              <Th>Team</Th>
              <Th className="num">GP</Th>
              <Th className="num">W</Th>
              <Th className="num">L</Th>
              <Th className="num">OTL</Th>
              <Th className="num">PTS</Th>
              <Th className="num">GF</Th>
              <Th className="num">GA</Th>
              <Th className="num">DIFF</Th>
            </tr>
          </thead>
          <tbody>
            {s.data.rows.map((r, i) => {
              const t = teams.data!.find((x) => x.id === r.team_id);
              const diff = r.goals_for - r.goals_against;
              return (
                <tr key={r.team_id} className={i === 0 ? "me" : ""}>
                  <Td className="rank">{i + 1}</Td>
                  <Td>
                    <span className="team-row">
                      {t && <Logo teamId={t.id} size={20} />}
                      <span className="nm">{t?.name ?? "—"}</span>
                      <span className="ab">{t?.abbreviation}</span>
                    </span>
                  </Td>
                  <Td className="num">{r.games_played}</Td>
                  <Td className="num">{r.wins}</Td>
                  <Td className="num">{r.losses}</Td>
                  <Td className="num">{r.ot_losses}</Td>
                  <Td className="num">
                    <b>{r.points}</b>
                  </Td>
                  <Td className="num">{r.goals_for}</Td>
                  <Td className="num">{r.goals_against}</Td>
                  <Td className="num" style={{ color: diff >= 0 ? "var(--green)" : "var(--red)", fontWeight: 700 }}>
                    {diff > 0 ? "+" : ""}
                    {diff}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </Card>

      <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <Card title="Season Averages">
          <div style={{ padding: "12px 16px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 16px", fontSize: 12 }}>
            <Stat k="Games" v={String(st.games_played)} />
            <Stat k="Penalties/game" v={num(st.penalties_per_game)} />
            <Stat k="Home goals" v={num(st.avg_home_goals)} />
            <Stat k="Away goals" v={num(st.avg_away_goals)} />
            <Stat k="Home shots" v={num(st.avg_home_shots)} />
            <Stat k="Away shots" v={num(st.avg_away_shots)} />
            <Stat k="PP G/G" v={num(st.pp_goals_per_game)} />
            <Stat k="SH G/G" v={num(st.sh_goals_per_game)} />
          </div>
        </Card>
      </div>
    </Shell>
  );
};

const Stat = ({ k, v }: { k: string; v: string }) => (
  <div className="kv">
    <span className="k">{k}</span>
    <span className="v">{v}</span>
  </div>
);

export const Route = createFileRoute("/season-complete")({ component: Done });
