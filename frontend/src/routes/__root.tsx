import { createRootRoute, Link, Outlet } from "@tanstack/react-router";

export const Route = createRootRoute({
  component: () => (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <nav className="flex gap-4 px-6 py-3 border-b bg-white">
        <Link to="/" className="font-bold">Hockey Manager</Link>
        <Link to="/schedule">Schedule</Link>
        <Link to="/standings">Standings</Link>
      </nav>
      <main className="p-6"><Outlet /></main>
    </div>
  ),
});
