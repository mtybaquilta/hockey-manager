import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Playoffs } from "../api/types";

export const usePlayoffs = () =>
  useQuery({ queryKey: ["playoffs"], queryFn: () => api.get<Playoffs>("/api/playoffs") });
