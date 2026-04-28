import type { ResultType } from "../api/types";

export const ResultBadge = ({ type }: { type: ResultType | null }) => {
  if (!type || type === "REG") return null;
  return <span className={`tag ${type === "OT" ? "tag-ot" : "tag-final"}`}>{type}</span>;
};
