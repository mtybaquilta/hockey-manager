import { useTeams } from "../queries/teams";
import { teamPrimary } from "../lib/team-colors";

export const Logo = ({ teamId, size = 24 }: { teamId: number; size?: number }) => {
  const teams = useTeams();
  const t = teams.data?.find((x) => x.id === teamId);
  if (!t) return null;
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
