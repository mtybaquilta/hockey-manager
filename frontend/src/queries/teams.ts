import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Roster, TeamSummary } from "../api/types";

export const useTeams = () =>
  useQuery({ queryKey: ["teams"], queryFn: () => api.get<TeamSummary[]>("/api/teams") });

export const useTeam = (id: number) =>
  useQuery({ queryKey: ["team", id], queryFn: () => api.get<TeamSummary>(`/api/teams/${id}`) });

export const useRoster = (id: number) =>
  useQuery({ queryKey: ["team", id, "roster"], queryFn: () => api.get<Roster>(`/api/teams/${id}/roster`) });
