import { createRootRoute, Outlet, useLocation, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useLeague } from "../queries/league";
import { useManagerProfile } from "../queries/manager";
import { NewLeagueScreen } from "../components/NewLeagueScreen";
import { CreateManagerScreen } from "../components/CreateManagerScreen";
import { HmApiError } from "../api/client";

const Layout = () => {
  const league = useLeague();
  const profile = useManagerProfile();
  const nav = useNavigate();
  const loc = useLocation();

  const noLeague =
    league.error instanceof HmApiError && league.error.code === "LeagueNotFound";

  // After league + profile loaded, redirect new users into the choose-team flow.
  useEffect(() => {
    if (noLeague) return;
    if (league.isLoading || profile.isLoading) return;
    if (!profile.data) return; // handled by the no-profile screen below
    if (profile.data.current_team_id == null && loc.pathname !== "/manager/choose-team") {
      nav({ to: "/manager/choose-team" });
    }
  }, [noLeague, league.isLoading, profile.isLoading, profile.data, loc.pathname, nav]);

  if (league.isLoading || profile.isLoading) {
    return <div style={{ padding: 24, color: "var(--ink-3)" }}>Loading league…</div>;
  }

  if (noLeague) {
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

  if (!profile.data) {
    return (
      <div className="chl-shell" style={{ gridTemplateColumns: "1fr" }}>
        <div className="chl-main">
          <div className="chl-content" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
            <CreateManagerScreen />
          </div>
        </div>
      </div>
    );
  }

  return <Outlet />;
};

export const Route = createRootRoute({ component: Layout });
