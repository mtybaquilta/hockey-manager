import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  DevelopmentSummary,
  GoalieCareer,
  PlayerDevelopmentHistory,
  SkaterCareer,
  StartNextSeasonResponse,
} from "../api/types";

export const useStartNextSeason = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<StartNextSeasonResponse>("/api/season/start-next"),
    onSuccess: () => {
      qc.invalidateQueries();
    },
  });
};

export const useDevelopmentSummary = (seasonId?: number) =>
  useQuery({
    queryKey: ["development-summary", seasonId ?? "latest"],
    queryFn: () =>
      api.get<DevelopmentSummary>(
        seasonId
          ? `/api/season/development-summary?season_id=${seasonId}`
          : "/api/season/development-summary"
      ),
  });

export const useSkaterDevelopment = (playerId: number) =>
  useQuery({
    queryKey: ["player-development", "skater", playerId],
    queryFn: () =>
      api.get<PlayerDevelopmentHistory>(`/api/players/skater/${playerId}/development`),
  });

export const useGoalieDevelopment = (playerId: number) =>
  useQuery({
    queryKey: ["player-development", "goalie", playerId],
    queryFn: () =>
      api.get<PlayerDevelopmentHistory>(`/api/players/goalie/${playerId}/development`),
  });

export const useSkaterCareer = (playerId: number) =>
  useQuery({
    queryKey: ["player-career", "skater", playerId],
    queryFn: () => api.get<SkaterCareer>(`/api/players/skater/${playerId}/career`),
  });

export const useGoalieCareer = (playerId: number) =>
  useQuery({
    queryKey: ["player-career", "goalie", playerId],
    queryFn: () => api.get<GoalieCareer>(`/api/players/goalie/${playerId}/career`),
  });
