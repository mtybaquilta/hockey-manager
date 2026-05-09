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
      qc.invalidateQueries({ queryKey: ["playoffs"] });
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

export interface SimToOptions {
  matchday?: number;
  stopAtPlayoffs?: boolean;
}

export const useSimTo = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (opts?: number | SimToOptions) => {
      const o: SimToOptions =
        typeof opts === "number" ? { matchday: opts } : opts ?? {};
      const params = new URLSearchParams();
      if (o.matchday !== undefined) params.set("matchday", String(o.matchday));
      if (o.stopAtPlayoffs) params.set("stop_at_playoffs", "true");
      const qs = params.toString();
      return api.post<SimToResponse>(
        qs ? `/api/season/sim-to?${qs}` : "/api/season/sim-to"
      );
    },
    onSuccess: () => {
      qc.invalidateQueries();
    },
  });
};
