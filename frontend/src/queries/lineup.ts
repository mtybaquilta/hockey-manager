import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Lineup, LineupSlots } from "../api/types";

export const useLineup = (teamId: number) =>
  useQuery({
    queryKey: ["team", teamId, "lineup"],
    queryFn: () => api.get<Lineup>(`/api/teams/${teamId}/lineup`),
  });

export const useUpdateLineup = (teamId: number) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slots: LineupSlots) => api.put<Lineup>(`/api/teams/${teamId}/lineup`, slots),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team", teamId, "lineup"] }),
  });
};
