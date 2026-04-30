import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { AdvanceResponse, SeasonStats, SeasonStatus } from "../api/types";

export const useSeasonStatus = () =>
  useQuery({ queryKey: ["season", "status"], queryFn: () => api.get<SeasonStatus>("/api/season/status") });

export const useSeasonStats = () =>
  useQuery({ queryKey: ["season", "stats"], queryFn: () => api.get<SeasonStats>("/api/season/stats") });

export const useAdvance = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<AdvanceResponse>("/api/season/advance"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schedule"] });
      qc.invalidateQueries({ queryKey: ["standings"] });
      qc.invalidateQueries({ queryKey: ["season", "status"] });
      qc.invalidateQueries({ queryKey: ["season", "stats"] });
      qc.invalidateQueries({ queryKey: ["league"] });
      qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "game" });
    },
  });
};

export interface SimToResponse {
  matchdays_simulated: number;
  games_simulated: number;
  current_matchday: number;
  season_status: "active" | "complete";
}

export const useSimTo = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (matchday?: number) =>
      api.post<SimToResponse>(
        matchday !== undefined ? `/api/season/sim-to?matchday=${matchday}` : "/api/season/sim-to"
      ),
    onSuccess: () => {
      qc.invalidateQueries();
    },
  });
};
