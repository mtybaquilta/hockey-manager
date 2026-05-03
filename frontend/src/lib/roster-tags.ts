import type { Goalie, Skater } from "../api/types";

export type RosterTag =
  | "Star"
  | "Top-6"
  | "Top-4"
  | "Prospect"
  | "Aging"
  | "Depth"
  | "Starter"
  | "Backup";

export const skaterOvr = (s: Skater): number =>
  Math.round(0.25 * s.shooting + 0.2 * s.passing + 0.2 * s.skating + 0.2 * s.defense + 0.15 * s.physical);

export const goalieOvr = (g: Goalie): number =>
  Math.round(0.3 * g.reflexes + 0.25 * g.positioning + 0.2 * g.rebound_control + 0.15 * g.puck_handling + 0.1 * g.mental);

const isForward = (pos: string) => pos !== "LD" && pos !== "RD";

export const computeSkaterTags = (skaters: Skater[]): Map<number, RosterTag> => {
  const ovrs = new Map(skaters.map((s) => [s.id, skaterOvr(s)]));
  const forwards = skaters.filter((s) => isForward(s.position)).sort((a, b) => ovrs.get(b.id)! - ovrs.get(a.id)!);
  const dmen = skaters.filter((s) => !isForward(s.position)).sort((a, b) => ovrs.get(b.id)! - ovrs.get(a.id)!);
  const top6 = new Set(forwards.slice(0, 6).map((s) => s.id));
  const top4 = new Set(dmen.slice(0, 4).map((s) => s.id));

  const tags = new Map<number, RosterTag>();
  for (const s of skaters) {
    const ovr = ovrs.get(s.id)!;
    if (ovr >= 85) tags.set(s.id, "Star");
    else if (s.age <= 23 && s.potential - ovr >= 8) tags.set(s.id, "Prospect");
    else if (isForward(s.position) && top6.has(s.id) && ovr >= 70) tags.set(s.id, "Top-6");
    else if (!isForward(s.position) && top4.has(s.id) && ovr >= 70) tags.set(s.id, "Top-4");
    else if (s.age >= 33 && ovr < 75) tags.set(s.id, "Aging");
    else tags.set(s.id, "Depth");
  }
  return tags;
};

export const computeGoalieTags = (goalies: Goalie[]): Map<number, RosterTag> => {
  const ovrs = new Map(goalies.map((g) => [g.id, goalieOvr(g)]));
  const sorted = [...goalies].sort((a, b) => ovrs.get(b.id)! - ovrs.get(a.id)!);
  const tags = new Map<number, RosterTag>();
  sorted.forEach((g, i) => {
    const ovr = ovrs.get(g.id)!;
    if (g.age <= 24 && g.potential - ovr >= 8) tags.set(g.id, "Prospect");
    else if (i === 0) tags.set(g.id, "Starter");
    else if (i === 1) tags.set(g.id, "Backup");
    else tags.set(g.id, "Depth");
  });
  return tags;
};

export const tagClass = (t: RosterTag): string => {
  switch (t) {
    case "Star": return "tag-star";
    case "Top-6":
    case "Top-4":
    case "Starter": return "tag-top";
    case "Prospect": return "tag-prospect";
    case "Aging": return "tag-aging";
    case "Backup": return "tag-backup";
    case "Depth": return "tag-depth";
  }
};
