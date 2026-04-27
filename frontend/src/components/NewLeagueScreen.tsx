import { useState } from "react";
import { useCreateLeague } from "../queries/league";
import { Button } from "./Button";
import { Card } from "./Card";

export const NewLeagueScreen = () => {
  const [seed, setSeed] = useState<string>("");
  const create = useCreateLeague();
  return (
    <Card title="Start a new league" className="max-w-md mx-auto">
      <p className="text-sm text-slate-600 mb-3">Generate 4 teams and an 18-game schedule.</p>
      <div className="flex gap-2 items-end">
        <label className="flex-1">
          <span className="block text-xs text-slate-500">Seed (optional)</span>
          <input
            className="border rounded px-2 py-1 w-full"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            placeholder="random"
          />
        </label>
        <Button disabled={create.isPending} onClick={() => create.mutate(seed ? Number(seed) : undefined)}>
          {create.isPending ? "Generating…" : "Create league"}
        </Button>
      </div>
    </Card>
  );
};
