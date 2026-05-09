import type { SkaterDetail, GoalieDetail } from "../api/types";

const ageBucket = (age: number): "young" | "prime" | "veteran" =>
  age <= 23 ? "young" : age >= 32 ? "veteran" : "prime";

const tier = (v: number): "elite" | "strong" | "average" | "weak" =>
  v >= 85 ? "elite" : v >= 75 ? "strong" : v >= 65 ? "average" : "weak";

export const skaterSnapshot = (p: SkaterDetail, ovr: number): string => {
  const a = p.attributes;
  const age = ageBucket(p.age);
  const top = (
    [
      ["skating", a.skating],
      ["shooting", a.shooting],
      ["passing", a.passing],
      ["defense", a.defense],
      ["physical", a.physical],
    ] as const
  )
    .slice()
    .sort((x, y) => y[1] - x[1]);
  const [strongName] = top[0];
  const [weakName] = top[top.length - 1];
  const upside = p.potential - ovr;

  const parts: string[] = [];
  if (age === "young" && upside >= 8) {
    parts.push(`Young high-upside ${labelFor(p.position)} still developing toward a ${p.potential} ceiling.`);
  } else if (age === "veteran") {
    parts.push(`Veteran ${labelFor(p.position)} with proven experience but limited room to grow.`);
  } else if (ovr >= 82) {
    parts.push(`Established top-line ${labelFor(p.position)} producing at a high level.`);
  } else if (ovr >= 72) {
    parts.push(`Reliable middle-six ${labelFor(p.position)} contributing in multiple areas.`);
  } else {
    parts.push(`Depth ${labelFor(p.position)} filling out the bottom of the roster.`);
  }

  parts.push(`Best trait is ${strongName} (${humanAttr(strongName, a)}); ${weakName} is the main weakness.`);

  if (a.shooting >= 80 && a.skating >= 80) {
    parts.push("Combines speed and finish to create offense off the rush.");
  } else if (a.passing >= 80) {
    parts.push("Vision and playmaking drive the line's offense.");
  } else if (a.defense >= 80) {
    parts.push("Defensive game is the calling card.");
  }

  return parts.join(" ");
};

export const goalieSnapshot = (g: GoalieDetail, ovr: number): string => {
  const a = g.attributes;
  const age = ageBucket(g.age);
  const upside = g.potential - ovr;
  const parts: string[] = [];
  if (age === "young" && upside >= 8) {
    parts.push(`Young goaltender with a ${g.potential} ceiling still being developed.`);
  } else if (age === "veteran") {
    parts.push("Veteran goaltender with limited remaining upside.");
  } else if (ovr >= 82) {
    parts.push("Established starter capable of stealing games.");
  } else {
    parts.push("Reliable depth option in net.");
  }
  if (a.reflexes >= 82) parts.push("Quick post-to-post reflexes.");
  if (a.positioning >= 82) parts.push("Excellent positional play.");
  if (a.mental < 70) parts.push("Mental game can wobble under pressure.");
  return parts.join(" ");
};

const labelFor = (pos: string): string => {
  switch (pos) {
    case "C":
      return "center";
    case "LW":
      return "left wing";
    case "RW":
      return "right wing";
    case "LD":
    case "RD":
      return "defenseman";
    default:
      return "skater";
  }
};

const humanAttr = (
  k: "skating" | "shooting" | "passing" | "defense" | "physical",
  a: SkaterDetail["attributes"],
): string => `${a[k]}`;

export const skaterStrengths = (p: SkaterDetail): string[] => {
  const a = p.attributes;
  const out: string[] = [];
  if (a.skating >= 82) out.push("Elite skating creates separation");
  if (a.shooting >= 82) out.push("Strong scoring touch and finishing");
  if (a.passing >= 82) out.push("High-end vision and playmaking");
  if (a.defense >= 82) out.push("Reliable defensively in own zone");
  if (a.physical >= 82) out.push("Wins puck battles consistently");
  if (out.length === 0 && tier(Math.max(a.skating, a.shooting, a.passing, a.defense, a.physical)) === "strong") {
    out.push("Well-rounded with no glaring weakness");
  }
  return out.slice(0, 4);
};

export const skaterWeaknesses = (p: SkaterDetail): string[] => {
  const a = p.attributes;
  const out: string[] = [];
  if (a.defense < 70) out.push("Defensive awareness needs work");
  if (a.physical < 65) out.push("Can be outmuscled in board battles");
  if (a.skating < 70) out.push("Lacks foot speed in transition");
  if (a.passing < 65) out.push("Limited playmaking instincts");
  if (a.shooting < 65) out.push("Struggles to finish chances");
  return out.slice(0, 3);
};

export const goalieStrengths = (g: GoalieDetail): string[] => {
  const a = g.attributes;
  const out: string[] = [];
  if (a.reflexes >= 82) out.push("Quick reflexes on second chances");
  if (a.positioning >= 82) out.push("Reads plays and squares to shooters");
  if (a.rebound_control >= 80) out.push("Controls rebounds into safe areas");
  if (a.puck_handling >= 78) out.push("Confident handling the puck");
  if (a.mental >= 82) out.push("Stays composed under pressure");
  return out.slice(0, 4);
};

export const goalieWeaknesses = (g: GoalieDetail): string[] => {
  const a = g.attributes;
  const out: string[] = [];
  if (a.rebound_control < 70) out.push("Tends to give up bad rebounds");
  if (a.puck_handling < 65) out.push("Hesitant playing the puck");
  if (a.mental < 70) out.push("Can spiral after a bad goal");
  if (a.positioning < 70) out.push("Positioning lapses on cross-ice plays");
  return out.slice(0, 3);
};
