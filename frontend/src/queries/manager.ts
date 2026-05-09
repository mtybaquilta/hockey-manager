import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ManagerProfile, TeamSelectOverview } from "../api/types";

export const useManagerProfile = () =>
  useQuery({
    queryKey: ["manager-profile"],
    queryFn: () => api.get<ManagerProfile | null>("/api/manager-profile"),
  });

export const useCreateManager = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.post<ManagerProfile>("/api/manager-profile", { name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["manager-profile"] }),
  });
};

export const useSetManagerTeam = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (team_id: number) =>
      api.put<ManagerProfile>("/api/manager-profile/team", { team_id }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["manager-profile"] });
      qc.invalidateQueries({ queryKey: ["league"] });
    },
  });
};

export const useSelectOverview = () =>
  useQuery({
    queryKey: ["teams", "select-overview"],
    queryFn: () => api.get<TeamSelectOverview[]>("/api/teams/select-overview"),
  });
