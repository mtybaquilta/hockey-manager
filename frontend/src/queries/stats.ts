import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  GoaliesStats,
  GoalieDetail,
  SkaterDetail,
  SkatersStats,
  TeamsStats,
} from "../api/types";

export const useSkaterStats = () =>
  useQuery({ queryKey: ["stats", "skaters"], queryFn: () => api.get<SkatersStats>("/api/stats/skaters") });

export const useGoalieStats = () =>
  useQuery({ queryKey: ["stats", "goalies"], queryFn: () => api.get<GoaliesStats>("/api/stats/goalies") });

export const useTeamStats = () =>
  useQuery({ queryKey: ["stats", "teams"], queryFn: () => api.get<TeamsStats>("/api/stats/teams") });

export const useSkaterDetail = (id: number) =>
  useQuery({ queryKey: ["player", "skater", id], queryFn: () => api.get<SkaterDetail>(`/api/players/skater/${id}`) });

export const useGoalieDetail = (id: number) =>
  useQuery({ queryKey: ["player", "goalie", id], queryFn: () => api.get<GoalieDetail>(`/api/players/goalie/${id}`) });
