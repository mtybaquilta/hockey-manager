import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  TradeEvaluateRequest,
  TradeEvaluateResponse,
  TradeExecuteResponse,
} from "../api/types";

export const useEvaluateTrade = () =>
  useMutation({
    mutationFn: (req: TradeEvaluateRequest) =>
      api.post<TradeEvaluateResponse>("/api/trades/evaluate", req),
  });

export const useExecuteTrade = (userTeamId: number | null, partnerTeamId: number | null) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: TradeEvaluateRequest) =>
      api.post<TradeExecuteResponse>("/api/trades/execute", req),
    onSuccess: (res) => {
      if (!res.accepted) return;
      qc.invalidateQueries({ queryKey: ["teams"] });
      qc.invalidateQueries({ queryKey: ["roster"] });
      qc.invalidateQueries({ queryKey: ["lineup"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      if (userTeamId != null) {
        qc.invalidateQueries({ queryKey: ["team", userTeamId] });
        qc.invalidateQueries({ queryKey: ["lineup", userTeamId] });
        qc.invalidateQueries({ queryKey: ["roster", userTeamId] });
      }
      if (partnerTeamId != null) {
        qc.invalidateQueries({ queryKey: ["team", partnerTeamId] });
        qc.invalidateQueries({ queryKey: ["lineup", partnerTeamId] });
        qc.invalidateQueries({ queryKey: ["roster", partnerTeamId] });
      }
    },
  });
};
