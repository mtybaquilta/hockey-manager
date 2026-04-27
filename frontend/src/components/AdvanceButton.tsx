import { useNavigate } from "@tanstack/react-router";
import { useAdvance, useSeasonStatus } from "../queries/season";
import { Button } from "./Button";

export const AdvanceButton = () => {
  const status = useSeasonStatus();
  const advance = useAdvance();
  const nav = useNavigate();
  if (!status.data) return null;
  if (status.data.status === "complete") {
    return <Button onClick={() => nav({ to: "/season-complete" })}>Season complete</Button>;
  }
  return (
    <Button
      disabled={advance.isPending}
      onClick={() =>
        advance.mutate(undefined, {
          onSuccess: (r) => {
            if (r.season_status === "complete") nav({ to: "/season-complete" });
          },
        })
      }
    >
      {advance.isPending ? "Simulating…" : "Advance matchday"}
    </Button>
  );
};
