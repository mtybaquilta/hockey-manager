import { useLeague } from "../queries/league";
import { useTeams } from "../queries/teams";
import { cn } from "../lib/cn";

export const TeamBadge = ({ teamId }: { teamId: number }) => {
  const teams = useTeams();
  const league = useLeague();
  const t = teams.data?.find((x) => x.id === teamId);
  if (!t) return <span>—</span>;
  const isUser = league.data?.user_team_id === teamId;
  return <span className={cn("font-mono", isUser && "text-blue-700 font-bold")}>{t.abbreviation}</span>;
};
