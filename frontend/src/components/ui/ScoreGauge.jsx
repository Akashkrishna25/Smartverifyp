import React from "react";
import { scoreColor } from "../../utils/formatters";

export default function ScoreGauge({ label, score, max = 100 }) {
  const pct = Math.min((score / max) * 100, 100);
  const color = score >= 70 ? "#16a34a" : score >= 40 ? "#d97706" : "#dc2626";
  return (
    <div className="flex flex-col items-center gap-2">
      <svg width="96" height="96" viewBox="0 0 96 96">
        <circle cx="48" cy="48" r="38" fill="none" stroke="#e2e8f0" strokeWidth="8" />
        <circle cx="48" cy="48" r="38" fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={`${2 * Math.PI * 38 * pct / 100} ${2 * Math.PI * 38 * (1 - pct / 100)}`}
          strokeLinecap="round"
          transform="rotate(-90 48 48)" />
        <text x="48" y="52" textAnchor="middle" fontSize="18" fontWeight="bold" fill={color}>
          {Math.round(score)}
        </text>
      </svg>
      <p className="text-sm text-slate-500 font-medium">{label}</p>
    </div>
  );
}
