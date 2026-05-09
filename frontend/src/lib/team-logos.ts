const logoModules = import.meta.glob("../assets/teams/*.{avif,png,svg,webp}", {
  eager: true,
  import: "default",
}) as Record<string, string>;

const byFile: Record<string, string> = Object.fromEntries(
  Object.entries(logoModules).map(([path, url]) => [path.split("/").pop()!, url]),
);

const ABBR_TO_FILE: Record<string, string> = {
  ANA: "ducks.avif",
  BOS: "bruins.avif",
  BUF: "sabres.avif",
  CGY: "flames.avif",
  CAR: "hurricanes.avif",
  CHI: "blackhawks.avif",
  COL: "avalance.avif",
  CBJ: "bluejackets.avif",
  DAL: "stars.avif",
  DET: "redwings.avif",
  EDM: "oilers.avif",
  FLA: "panthers.avif",
  LAK: "lakings.avif",
  MIN: "wild.avif",
  MTL: "canadians.avif",
  NSH: "predators.avif",
  NJD: "devils.avif",
  NYI: "islanders.avif",
  NYR: "rangers.avif",
  OTT: "senators.avif",
  PHI: "flyers.avif",
  PIT: "penguins.avif",
  SJS: "sharks.avif",
  SEA: "kraken.avif",
  STL: "blues.avif",
  TBL: "lightning.avif",
  TOR: "mapleleafs.avif",
  UTA: "utah.png",
  VAN: "canucks.avif",
  VGK: "vegas.avif",
  WSH: "capitals.avif",
  WPG: "jets.avif",
};

export const logoForAbbr = (abbr: string): string | undefined => {
  const file = ABBR_TO_FILE[abbr];
  return file ? byFile[file] : undefined;
};
