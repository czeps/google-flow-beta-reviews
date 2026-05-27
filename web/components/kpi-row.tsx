import { KpiCard } from "./kpi-card";
import type { CountrySlice } from "@/lib/types";

export function KpiRow({ slice }: { slice: CountrySlice }) {
  const { kpis } = slice;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        label="Total reviews"
        value={kpis.total_reviews.toLocaleString()}
        subtitle={
          kpis.date_range.start
            ? `${kpis.date_range.start} to ${kpis.date_range.end}`
            : "—"
        }
      />
      <KpiCard
        label="Average score"
        value={`${kpis.avg_score.toFixed(2)}/5`}
        subtitle={`${Math.round(kpis.pct_positive * 100)}% positive (4-5 stars)`}
      />
      <KpiCard
        label="Features praised"
        value={kpis.features_praised.toString()}
        subtitle={`${kpis.praised_mentions} total mentions`}
      />
      <KpiCard
        label="Issues to fix"
        value={kpis.issues_count.toString()}
        subtitle={`Themes with ≥5 negative mentions`}
      />
    </div>
  );
}
