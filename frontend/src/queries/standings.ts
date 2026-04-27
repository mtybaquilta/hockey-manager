import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Standings } from "../api/types";

export const useStandings = () =>
  useQuery({ queryKey: ["standings"], queryFn: () => api.get<Standings>("/api/standings") });
