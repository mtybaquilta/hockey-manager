import { createRootRoute, Outlet } from "@tanstack/react-router";
import { useLeague } from "../queries/league";
import { NewLeagueScreen } from "../components/NewLeagueScreen";
import { HmApiError } from "../api/client";

const Layout = () => {
  const league = useLeague();
  if (league.isLoading) {
    return (
      <div style={{ padding: 24, color: "var(--ink-3)" }}>Loading league…</div>
    );
  }
  if (league.error instanceof HmApiError && league.error.code === "LeagueNotFound") {
    return (
      <div className="chl-shell" style={{ gridTemplateColumns: "1fr" }}>
        <div className="chl-main">
          <div className="chl-content" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
            <NewLeagueScreen />
          </div>
        </div>
      </div>
    );
  }
  return <Outlet />;
};

export const Route = createRootRoute({ component: Layout });
