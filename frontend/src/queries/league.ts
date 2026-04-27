import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { League } from "../api/types";

export const useLeague = () =>
  useQuery({ queryKey: ["league"], queryFn: () => api.get<League>("/api/league"), retry: false });

export const useCreateLeague = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (seed?: number) => api.post<League>("/api/league", { seed }),
    onSuccess: () => qc.invalidateQueries(),
  });
};

export const useSetUserTeam = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (team_id: number) => api.put<League>("/api/league/user-team", { team_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["league"] }),
  });
};
