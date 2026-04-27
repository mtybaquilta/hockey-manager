import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { AdvanceResponse, SeasonStatus } from "../api/types";

export const useSeasonStatus = () =>
  useQuery({ queryKey: ["season", "status"], queryFn: () => api.get<SeasonStatus>("/api/season/status") });

export const useAdvance = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<AdvanceResponse>("/api/season/advance"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schedule"] });
      qc.invalidateQueries({ queryKey: ["standings"] });
      qc.invalidateQueries({ queryKey: ["season", "status"] });
      qc.invalidateQueries({ queryKey: ["league"] });
      qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "game" });
    },
  });
};
