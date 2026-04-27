import { createRootRoute, Link, Outlet } from "@tanstack/react-router";
import { useLeague } from "../queries/league";
import { NewLeagueScreen } from "../components/NewLeagueScreen";
import { AdvanceButton } from "../components/AdvanceButton";
import { HmApiError } from "../api/client";

const Layout = () => {
  const league = useLeague();
  if (league.isLoading) return <div className="p-6">Loading…</div>;
  if (league.error instanceof HmApiError && league.error.code === "LeagueNotFound") {
    return <div className="p-6"><NewLeagueScreen /></div>;
  }
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <nav className="flex gap-4 px-6 py-3 border-b bg-white items-center">
        <Link to="/" className="font-bold">Hockey Manager</Link>
        <Link to="/schedule">Schedule</Link>
        <Link to="/standings">Standings</Link>
        {league.data?.user_team_id != null && (
          <Link to="/team/$teamId" params={{ teamId: String(league.data.user_team_id) }}>My team</Link>
        )}
        <div className="ml-auto"><AdvanceButton /></div>
      </nav>
      <main className="p-6"><Outlet /></main>
    </div>
  );
};

export const Route = createRootRoute({ component: Layout });
