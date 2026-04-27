import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Schedule } from "../api/types";

export const useSchedule = () =>
  useQuery({ queryKey: ["schedule"], queryFn: () => api.get<Schedule>("/api/schedule") });
