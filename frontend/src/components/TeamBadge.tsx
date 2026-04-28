import { useTeams } from "../queries/teams";
import { Logo } from "./Logo";

export const TeamBadge = ({ teamId, showCity = false }: { teamId: number; showCity?: boolean }) => {
  const teams = useTeams();
  const t = teams.data?.find((x) => x.id === teamId);
  if (!t) return <span>—</span>;
  return (
    <span className="team-row">
      <Logo teamId={teamId} size={18} />
      <span className="nm">{showCity ? t.name : t.name}</span>
      <span className="ab">{t.abbreviation}</span>
    </span>
  );
};
