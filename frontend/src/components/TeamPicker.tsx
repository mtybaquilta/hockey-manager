import { useLeague, useSetUserTeam } from "../queries/league";
import { Button } from "./Button";
import { Card } from "./Card";

export const TeamPicker = () => {
  const league = useLeague();
  const setTeam = useSetUserTeam();
  if (!league.data) return null;
  return (
    <Card title="Pick your team" className="max-w-2xl mx-auto">
      <ul className="grid grid-cols-2 gap-3">
        {league.data.teams.map((t) => (
          <li key={t.id} className="flex items-center justify-between border rounded p-3">
            <div>
              <div className="font-semibold">{t.name}</div>
              <div className="text-xs text-slate-500">{t.abbreviation}</div>
            </div>
            <Button onClick={() => setTeam.mutate(t.id)}>Choose</Button>
          </li>
        ))}
      </ul>
    </Card>
  );
};
