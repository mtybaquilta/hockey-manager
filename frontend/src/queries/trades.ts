import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  TradeBlockEntry,
  TradeProposalRequest,
  TradeProposalResponse,
} from "../api/types";

export const useTradeBlock = () =>
  useQuery({
    queryKey: ["trade-block"],
    queryFn: () => api.get<TradeBlockEntry[]>("/api/trade-block"),
  });

export const useProposeTrade = (userTeamId: number | null) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: TradeProposalRequest) =>
      api.post<TradeProposalResponse>("/api/trades/propose", req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trade-block"] });
      qc.invalidateQueries({ queryKey: ["teams"] });
      if (userTeamId != null) {
        qc.invalidateQueries({ queryKey: ["team", userTeamId] });
        qc.invalidateQueries({ queryKey: ["lineup", userTeamId] });
      }
      // Also invalidate the receiving team's roster/lineup if we know it.
      // The trade-block refetch covers most other team-id cases.
    },
  });
};
