import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  FreeAgentFilters,
  FreeAgentGoalie,
  FreeAgentSkater,
} from "../api/types";

const buildQs = (f: FreeAgentFilters) => {
  const p = new URLSearchParams();
  if (f.position) p.set("position", f.position);
  if (f.min_ovr != null) p.set("min_ovr", String(f.min_ovr));
  if (f.min_potential != null) p.set("min_potential", String(f.min_potential));
  if (f.max_age != null) p.set("max_age", String(f.max_age));
  if (f.sort) p.set("sort", f.sort);
  if (f.order) p.set("order", f.order);
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const useFreeAgentSkaters = (filters: FreeAgentFilters) =>
  useQuery({
    queryKey: ["free-agents", "skaters", filters],
    queryFn: () =>
      api.get<FreeAgentSkater[]>(`/api/free-agents/skaters${buildQs(filters)}`),
  });

export const useFreeAgentGoalies = (filters: Omit<FreeAgentFilters, "position">) =>
  useQuery({
    queryKey: ["free-agents", "goalies", filters],
    queryFn: () =>
      api.get<FreeAgentGoalie[]>(`/api/free-agents/goalies${buildQs(filters)}`),
  });

const useInvalidateOnSettle = (teamId: number) => {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["free-agents"] });
    qc.invalidateQueries({ queryKey: ["team", teamId] });
    qc.invalidateQueries({ queryKey: ["lineup", teamId] });
  };
};

export const useSignSkater = (teamId: number) => {
  const onSettle = useInvalidateOnSettle(teamId);
  return useMutation({
    mutationFn: (skaterId: number) =>
      api.post(`/api/teams/${teamId}/sign/skater/${skaterId}`),
    onSuccess: onSettle,
  });
};

export const useSignGoalie = (teamId: number) => {
  const onSettle = useInvalidateOnSettle(teamId);
  return useMutation({
    mutationFn: (goalieId: number) =>
      api.post(`/api/teams/${teamId}/sign/goalie/${goalieId}`),
    onSuccess: onSettle,
  });
};

export const useReleaseSkater = (teamId: number) => {
  const onSettle = useInvalidateOnSettle(teamId);
  return useMutation({
    mutationFn: (skaterId: number) =>
      api.post(`/api/teams/${teamId}/release/skater/${skaterId}`),
    onSuccess: onSettle,
  });
};

export const useReleaseGoalie = (teamId: number) => {
  const onSettle = useInvalidateOnSettle(teamId);
  return useMutation({
    mutationFn: (goalieId: number) =>
      api.post(`/api/teams/${teamId}/release/goalie/${goalieId}`),
    onSuccess: onSettle,
  });
};
