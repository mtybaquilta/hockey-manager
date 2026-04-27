import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { GameDetail } from "../api/types";

export const useGame = (id: number) =>
  useQuery({ queryKey: ["game", id], queryFn: () => api.get<GameDetail>(`/api/games/${id}`) });
