export const formatCurrency = (v) =>
  v != null ? `₹ ${Number(v).toLocaleString("en-IN")}` : "N/A";

export const formatDate = (d) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";

export const statusBadge = (status) => {
  const map = {
    approved:      "badge-approved",
    rejected:      "badge-rejected",
    pending:       "badge-pending",
    manual_review: "badge-manual_review",
  };
  return map[status] || "badge-pending";
};

export const scoreColor = (score) => {
  if (score >= 70) return "text-green-600";
  if (score >= 40) return "text-yellow-600";
  return "text-red-600";
};
