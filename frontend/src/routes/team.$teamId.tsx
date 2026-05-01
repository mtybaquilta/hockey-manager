import { createFileRoute, Link, Outlet, useMatchRoute } from "@tanstack/react-router";
import { useState } from "react";
// Skater/goalie names link to the player detail page.
import { Pagination, usePager } from "../components/Pagination";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { attrClass } from "../lib/team-colors";
import type { GameplanLineUsage, GameplanStyle } from "../api/types";
import { useTeamGameplan, useUpdateTeamGameplan } from "../queries/gameplan";
import { useLeague } from "../queries/league";
import { useRoster } from "../queries/teams";

const GameplanCard = ({ teamId }: { teamId: number }) => {
  const q = useTeamGameplan(teamId);
  const m = useUpdateTeamGameplan(teamId);
  const [style, setStyle] = useState<GameplanStyle | null>(null);
  const [lineUsage, setLineUsage] = useState<GameplanLineUsage | null>(null);

  if (!q.data) return null;
  const gp = q.data;
  const currentStyle = style ?? gp.style;
  const currentLine = lineUsage ?? gp.line_usage;
  const dirty = currentStyle !== gp.style || currentLine !== gp.line_usage;

  if (!gp.editable) {
    return (
      <div className="card" style={{ marginTop: 14 }}>
        <div className="ribbon-h">
          <span className="accent" />
          Gameplan
        </div>
        <div style={{ padding: "14px 16px", display: "flex", gap: 16 }}>
          <span className="chip">{gp.style}</span>
          <span className="chip">{gp.line_usage}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ marginTop: 14 }}>
      <div className="ribbon-h">
        <span className="accent" />
        Gameplan · Applies to future games
      </div>
      <div
        style={{
          padding: "14px 16px",
          display: "grid",
          gap: 10,
          gridTemplateColumns: "auto 1fr",
          alignItems: "center",
        }}
      >
        <label>Style</label>
        <select
          value={currentStyle}
          onChange={(e) => setStyle(e.target.value as GameplanStyle)}
        >
          {(["balanced", "offensive", "defensive", "physical"] as GameplanStyle[]).map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <label>Line usage</label>
        <select
          value={currentLine}
          onChange={(e) => setLineUsage(e.target.value as GameplanLineUsage)}
        >
          {(["balanced", "ride_top_lines", "roll_all_lines"] as GameplanLineUsage[]).map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <div />
        <button
          className="btn btn-primary"
          disabled={!dirty || m.isPending}
          onClick={() =>
            m.mutate(
              { style: currentStyle, line_usage: currentLine },
              {
                onSuccess: () => {
                  setStyle(null);
                  setLineUsage(null);
                },
              },
            )
          }
        >
          {m.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
};

const TeamPage = () => {
  const { teamId } = Route.useParams();
  const id = Number(teamId);
  const roster = useRoster(id);
  const league = useLeague();
  const matchRoute = useMatchRoute();
  const isChild = matchRoute({ to: "/team/$teamId/lineup", params: { teamId } });
  const F = roster.data?.skaters.filter((s) => s.position !== "LD" && s.position !== "RD") ?? [];
  const D = roster.data?.skaters.filter((s) => s.position === "LD" || s.position === "RD") ?? [];
  const G = roster.data?.goalies ?? [];
  const fPager = usePager(F);
  const dPager = usePager(D);
  const gPager = usePager(G);
  if (isChild) return <Outlet />;
  if (!roster.data || !league.data) {
    return <Shell crumbs={["Continental Hockey League", "My Team"]}>Loading…</Shell>;
  }
  const isUser = league.data.user_team_id === id;

  const SkaterRow = ({ p }: { p: (typeof F)[number] }) => {
    const ovr = Math.round(0.25 * p.shooting + 0.2 * p.passing + 0.2 * p.skating + 0.2 * p.defense + 0.15 * p.physical);
    return (
      <tr>
        <Td>
          <Link to="/player/skater/$id" params={{ id: String(p.id) }} style={{ fontWeight: 700, color: "var(--ink)" }}>
            {p.name}
          </Link>
        </Td>
        <Td style={{ color: "var(--ink-3)" }}>{p.position}</Td>
        <Td className="num">{p.age}</Td>
        <Td className="num">
          <span className={`chip ${attrClass(ovr)}`}>{ovr}</span>
        </Td>
        <Td className="num">
          <span className={`chip ${attrClass(p.skating)}`}>{p.skating}</span>
        </Td>
        <Td className="num">
          <span className={`chip ${attrClass(p.shooting)}`}>{p.shooting}</span>
        </Td>
        <Td className="num">
          <span className={`chip ${attrClass(p.passing)}`}>{p.passing}</span>
        </Td>
        <Td className="num">
          <span className={`chip ${attrClass(p.defense)}`}>{p.defense}</span>
        </Td>
        <Td className="num">
          <span className={`chip ${attrClass(p.physical)}`}>{p.physical}</span>
        </Td>
      </tr>
    );
  };

  const goalieOvr = (g: (typeof G)[number]) =>
    Math.round(0.3 * g.reflexes + 0.25 * g.positioning + 0.2 * g.rebound_control + 0.15 * g.puck_handling + 0.1 * g.mental);

  return (
    <Shell
      crumbs={["Continental Hockey League", "My Team"]}
      topRight={
        isUser && (
          <Link to="/team/$teamId/lineup" params={{ teamId }} className="btn btn-primary">
            Edit Lineup →
          </Link>
        )
      }
    >
      <div className="section-h">
        <h1>{roster.data.team.name}</h1>
        <span className="sub">
          {roster.data.skaters.length + roster.data.goalies.length} active · {roster.data.team.abbreviation}
        </span>
      </div>

      <div className="card">
        <div className="ribbon-h">
          <span className="accent" />
          Forwards · {F.length}
        </div>
        <Table>
          <thead>
            <tr>
              <Th>Player</Th>
              <Th>Pos</Th>
              <Th className="num">Age</Th>
              <Th className="num">OVR</Th>
              <Th className="num">SK</Th>
              <Th className="num">SH</Th>
              <Th className="num">PS</Th>
              <Th className="num">DF</Th>
              <Th className="num">PH</Th>
            </tr>
          </thead>
          <tbody>{fPager.slice.map((p) => <SkaterRow key={p.id} p={p} />)}</tbody>
        </Table>
        <Pagination {...fPager} onPage={fPager.setPage} />
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="ribbon-h">
          <span className="accent" />
          Defense · {D.length}
        </div>
        <Table>
          <thead>
            <tr>
              <Th>Player</Th>
              <Th>Pos</Th>
              <Th className="num">Age</Th>
              <Th className="num">OVR</Th>
              <Th className="num">SK</Th>
              <Th className="num">SH</Th>
              <Th className="num">PS</Th>
              <Th className="num">DF</Th>
              <Th className="num">PH</Th>
            </tr>
          </thead>
          <tbody>{dPager.slice.map((p) => <SkaterRow key={p.id} p={p} />)}</tbody>
        </Table>
        <Pagination {...dPager} onPage={dPager.setPage} />
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="ribbon-h">
          <span className="accent" />
          Goaltenders · {G.length}
        </div>
        <Table>
          <thead>
            <tr>
              <Th>Player</Th>
              <Th className="num">Age</Th>
              <Th className="num">OVR</Th>
              <Th className="num">RX</Th>
              <Th className="num">PO</Th>
              <Th className="num">RC</Th>
              <Th className="num">PH</Th>
              <Th className="num">ME</Th>
            </tr>
          </thead>
          <tbody>
            {gPager.slice.map((g) => {
              const ovr = goalieOvr(g);
              return (
                <tr key={g.id}>
                  <Td>
                    <Link to="/player/goalie/$id" params={{ id: String(g.id) }} style={{ fontWeight: 700, color: "var(--ink)" }}>
                      {g.name}
                    </Link>
                  </Td>
                  <Td className="num">{g.age}</Td>
                  <Td className="num">
                    <span className={`chip ${attrClass(ovr)}`}>{ovr}</span>
                  </Td>
                  <Td className="num">
                    <span className={`chip ${attrClass(g.reflexes)}`}>{g.reflexes}</span>
                  </Td>
                  <Td className="num">
                    <span className={`chip ${attrClass(g.positioning)}`}>{g.positioning}</span>
                  </Td>
                  <Td className="num">
                    <span className={`chip ${attrClass(g.rebound_control)}`}>{g.rebound_control}</span>
                  </Td>
                  <Td className="num">
                    <span className={`chip ${attrClass(g.puck_handling)}`}>{g.puck_handling}</span>
                  </Td>
                  <Td className="num">
                    <span className={`chip ${attrClass(g.mental)}`}>{g.mental}</span>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
        <Pagination {...gPager} onPage={gPager.setPage} />
      </div>

      <GameplanCard teamId={id} />
    </Shell>
  );
};

export const Route = createFileRoute("/team/$teamId")({ component: TeamPage });
