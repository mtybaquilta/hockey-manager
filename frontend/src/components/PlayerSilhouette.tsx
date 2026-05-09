import { teamPrimary } from "../lib/team-colors";

export const PlayerSilhouette = ({
  teamId,
  size = 96,
}: {
  teamId: number | null;
  size?: number;
}) => {
  const bg = teamId != null ? teamPrimary(String(teamId)) : "#37474F";
  const inner = "rgba(255,255,255,0.18)";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 96 96"
      role="img"
      aria-label="Player silhouette"
      style={{ display: "block", borderRadius: 8 }}
    >
      <rect width="96" height="96" rx="8" fill={bg} />
      <circle cx="48" cy="36" r="14" fill={inner} />
      <path d="M20 86 C 24 64, 40 58, 48 58 C 56 58, 72 64, 76 86 Z" fill={inner} />
    </svg>
  );
};
