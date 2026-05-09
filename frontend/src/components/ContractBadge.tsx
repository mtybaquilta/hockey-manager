import type { Contract } from "../api/types";

type Props = {
  contract: Contract | null | undefined;
  currentYear: number;
};

export const ContractBadge = ({ contract, currentYear }: Props) => {
  if (!contract) {
    return <span style={{ fontSize: 11, color: "var(--ink-3)" }}>UFA</span>;
  }
  const yrs = Math.max(0, contract.expires_after_year - currentYear + 1);
  const m = (contract.salary / 1000).toFixed(2);
  return (
    <span style={{ fontSize: 11, color: "var(--ink-2)" }}>
      {yrs}y · ${m}M
      {contract.no_trade_clause && (
        <span
          style={{
            marginLeft: 6,
            padding: "1px 6px",
            borderRadius: 3,
            background: "rgba(245, 158, 11, 0.15)",
            color: "#b45309",
            fontWeight: 600,
          }}
        >
          NTC
        </span>
      )}
    </span>
  );
};
