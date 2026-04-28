// Deterministic team color from id/abbr — backend doesn't ship brand colors.
const PALETTE = [
  "#0B2545", "#13315C", "#1E3A8A", "#2D2A24",
  "#37474F", "#3F4B5B", "#0F4C3A", "#7C2D12",
];

export const teamPrimary = (key: string | number): string => {
  const s = String(key);
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
};

export const attrClass = (v: number) => (v >= 85 ? "hi" : v < 70 ? "lo" : "");
