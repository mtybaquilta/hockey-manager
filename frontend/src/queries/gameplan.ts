import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Gameplan, GameplanLineUsage, GameplanStyle } from "../api/types";

export const useTeamGameplan = (teamId: number) =>
  useQuery({
    queryKey: ["team-gameplan", teamId],
    queryFn: () => api.get<Gameplan>(`/api/teams/${teamId}/gameplan`),
  });

export const useAllGameplans = () =>
  useQuery({
    queryKey: ["gameplans"],
    queryFn: () => api.get<{ rows: Gameplan[] }>(`/api/gameplans`),
  });

export const useUpdateTeamGameplan = (teamId: number) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { style: GameplanStyle; line_usage: GameplanLineUsage }) =>
      api.put<Gameplan>(`/api/teams/${teamId}/gameplan`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["team-gameplan", teamId] });
      qc.invalidateQueries({ queryKey: ["gameplans"] });
      qc.invalidateQueries({ queryKey: ["schedule"] });
      qc.invalidateQueries({ queryKey: ["standings"] });
    },
  });
};
