import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import { Button } from "../components/Button";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { attrClass } from "../lib/team-colors";
import { useLeague } from "../queries/league";
import {
  useFreeAgentGoalies,
  useFreeAgentSkaters,
  useSignGoalie,
  useSignSkater,
} from "../queries/free-agents";
import type { FreeAgentFilters, Position } from "../api/types";

const POSITIONS: Position[] = ["LW", "C", "RW", "LD", "RD"];

const numberOrUndef = (v: string): number | undefined =>
  v === "" ? undefined : Number(v);

const FreeAgentsPage = () => {
  const league = useLeague();
  const userTeamId = league.data?.user_team_id ?? null;
  const [tab, setTab] = useState<"skaters" | "goalies">("skaters");
  const [filters, setFilters] = useState<FreeAgentFilters>({
    sort: "ovr",
    order: "desc",
  });

  const skaters = useFreeAgentSkaters(filters);
  const goalies = useFreeAgentGoalies({
    min_ovr: filters.min_ovr,
    min_potential: filters.min_potential,
    max_age: filters.max_age,
    sort: filters.sort === "position" ? "ovr" : filters.sort,
    order: filters.order,
  });

  const signSkater = useSignSkater(userTeamId ?? 0);
  const signGoalie = useSignGoalie(userTeamId ?? 0);

  const update = <K extends keyof FreeAgentFilters>(
    k: K,
    v: FreeAgentFilters[K],
  ) => setFilters((f) => ({ ...f, [k]: v }));

  const canSign = userTeamId != null;

  return (
    <Shell crumbs={["Continental Hockey League", "Free Agents"]}>
      <div className="section-h">
        <h1>Free Agents</h1>
        <span className="sub">Sign players to your team</span>
      </div>

      <div className="card" style={{ padding: "12px 16px", marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <Button
            variant={tab === "skaters" ? "primary" : "default"}
            onClick={() => setTab("skaters")}
          >
            Skaters
          </Button>
          <Button
            variant={tab === "goalies" ? "primary" : "default"}
            onClick={() => setTab("goalies")}
          >
            Goalies
          </Button>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          {tab === "skaters" && (
            <select
              value={filters.position ?? ""}
              onChange={(e) =>
                update("position", (e.target.value || undefined) as Position | undefined)
              }
            >
              <option value="">All positions</option>
              {POSITIONS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          )}
          <input
            type="number"
            placeholder="Min OVR"
            value={filters.min_ovr ?? ""}
            onChange={(e) => update("min_ovr", numberOrUndef(e.target.value))}
            style={{ width: 100 }}
          />
          <input
            type="number"
            placeholder="Min POT"
            value={filters.min_potential ?? ""}
            onChange={(e) => update("min_potential", numberOrUndef(e.target.value))}
            style={{ width: 100 }}
          />
          <input
            type="number"
            placeholder="Max age"
            value={filters.max_age ?? ""}
            onChange={(e) => update("max_age", numberOrUndef(e.target.value))}
            style={{ width: 100 }}
          />
          <select
            value={filters.sort ?? "ovr"}
            onChange={(e) =>
              update("sort", e.target.value as FreeAgentFilters["sort"])
            }
          >
            <option value="ovr">OVR</option>
            <option value="potential">POT</option>
            <option value="age">Age</option>
            {tab === "skaters" && <option value="position">Position</option>}
          </select>
          <select
            value={filters.order ?? "desc"}
            onChange={(e) =>
              update("order", e.target.value as "asc" | "desc")
            }
          >
            <option value="desc">Desc</option>
            <option value="asc">Asc</option>
          </select>
        </div>

        {!canSign && (
          <div style={{ marginTop: 12, color: "var(--ink-3)" }}>
            Set a user team to sign players.
          </div>
        )}
      </div>

      {tab === "skaters" ? (
        <div className="card">
          <div className="ribbon-h">
            <span className="accent" />
            Skaters · {skaters.data?.length ?? 0}
          </div>
          <Table>
            <thead>
              <tr>
                <Th>Player</Th>
                <Th>Pos</Th>
                <Th className="num">Age</Th>
                <Th className="num">OVR</Th>
                <Th className="num">POT</Th>
                <Th className="num">SK</Th>
                <Th className="num">SH</Th>
                <Th className="num">PS</Th>
                <Th className="num">DF</Th>
                <Th className="num">PH</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {(skaters.data ?? []).map((s) => (
                <tr key={s.id}>
                  <Td style={{ fontWeight: 700, color: "var(--ink)" }}>{s.name}</Td>
                  <Td style={{ color: "var(--ink-3)" }}>{s.position}</Td>
                  <Td className="num">{s.age}</Td>
                  <Td className="num"><span className={`chip ${attrClass(s.ovr)}`}>{s.ovr}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(s.potential)}`}>{s.potential}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(s.skating)}`}>{s.skating}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(s.shooting)}`}>{s.shooting}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(s.passing)}`}>{s.passing}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(s.defense)}`}>{s.defense}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(s.physical)}`}>{s.physical}</span></Td>
                  <Td>
                    <Button
                      onClick={() => signSkater.mutate(s.id)}
                      disabled={!canSign || signSkater.isPending}
                    >
                      Sign
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      ) : (
        <div className="card">
          <div className="ribbon-h">
            <span className="accent" />
            Goalies · {goalies.data?.length ?? 0}
          </div>
          <Table>
            <thead>
              <tr>
                <Th>Player</Th>
                <Th className="num">Age</Th>
                <Th className="num">OVR</Th>
                <Th className="num">POT</Th>
                <Th className="num">RX</Th>
                <Th className="num">PO</Th>
                <Th className="num">RC</Th>
                <Th className="num">PH</Th>
                <Th className="num">ME</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {(goalies.data ?? []).map((g) => (
                <tr key={g.id}>
                  <Td style={{ fontWeight: 700, color: "var(--ink)" }}>{g.name}</Td>
                  <Td className="num">{g.age}</Td>
                  <Td className="num"><span className={`chip ${attrClass(g.ovr)}`}>{g.ovr}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(g.potential)}`}>{g.potential}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(g.reflexes)}`}>{g.reflexes}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(g.positioning)}`}>{g.positioning}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(g.rebound_control)}`}>{g.rebound_control}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(g.puck_handling)}`}>{g.puck_handling}</span></Td>
                  <Td className="num"><span className={`chip ${attrClass(g.mental)}`}>{g.mental}</span></Td>
                  <Td>
                    <Button
                      onClick={() => signGoalie.mutate(g.id)}
                      disabled={!canSign || signGoalie.isPending}
                    >
                      Sign
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
    </Shell>
  );
};

export const Route = createFileRoute("/free-agents")({ component: FreeAgentsPage });
