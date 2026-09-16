import React from "react";
import { statusBadge } from "../../utils/formatters";

const LABELS = {
  approved:      "Approved",
  rejected:      "Rejected",
  pending:       "Pending",
  manual_review: "Manual Review",
};

export default function StatusBadge({ status }) {
  return (
    <span className={statusBadge(status)}>
      {LABELS[status] || status}
    </span>
  );
}
