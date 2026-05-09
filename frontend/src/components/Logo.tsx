import { useTeams } from "../queries/teams";
import { teamPrimary } from "../lib/team-colors";
import { logoForAbbr } from "../lib/team-logos";

export const Logo = ({ teamId, size = 24 }: { teamId: number; size?: number }) => {
  const teams = useTeams();
  const t = teams.data?.find((x) => x.id === teamId);
  if (!t) return null;
  const src = logoForAbbr(t.abbreviation);
  if (src) {
    return (
      <span
        className="logo logo-img"
        style={{ width: size, height: size, background: "transparent", border: "none", boxShadow: "none" }}
      >
        <img
          src={src}
          alt={t.abbreviation}
          style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
        />
      </span>
    );
  }
  return (
    <span
      className="logo"
      style={{ width: size, height: size, background: teamPrimary(t.abbreviation), fontSize: size * 0.36 }}
    >
      <span style={{ color: "#fff", letterSpacing: "0.02em" }}>{t.abbreviation}</span>
    </span>
  );
};

export const TeamRow = ({ teamId, showName = true }: { teamId: number; showName?: boolean }) => {
  const teams = useTeams();
  const t = teams.data?.find((x) => x.id === teamId);
  if (!t) return <span>—</span>;
  return (
    <span className="team-row">
      <Logo teamId={teamId} size={20} />
      {showName && <span className="nm">{t.name}</span>}
      <span className="ab">{t.abbreviation}</span>
    </span>
  );
};
