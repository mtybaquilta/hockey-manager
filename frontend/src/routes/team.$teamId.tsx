import { createFileRoute, Link, Outlet, useMatchRoute } from "@tanstack/react-router";
// Skater/goalie names link to the player detail page.
import { Pagination, usePager } from "../components/Pagination";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { attrClass } from "../lib/team-colors";
import { useLeague } from "../queries/league";
import { useRoster } from "../queries/teams";

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
    </Shell>
  );
};

export const Route = createFileRoute("/team/$teamId")({ component: TeamPage });
