import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { GameDetail } from "../api/types";

export const useGame = (id: number) =>
  useQuery({ queryKey: ["game", id], queryFn: () => api.get<GameDetail>(`/api/games/${id}`) });

export const useSimulateGame = (id: number) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<GameDetail>(`/api/games/${id}/simulate`),
    onSuccess: (data) => {
      qc.setQueryData(["game", id], data);
      qc.invalidateQueries({ queryKey: ["schedule"] });
      qc.invalidateQueries({ queryKey: ["standings"] });
      qc.invalidateQueries({ queryKey: ["league"] });
      qc.invalidateQueries({ queryKey: ["season", "stats"] });
      qc.invalidateQueries({ queryKey: ["playoffs"] });
    },
  });
};
