import type { FeatureSummary } from "@/lib/types";

type Variant = "praised" | "issue";

export function FeatureRow({
  feature,
  maxValue,
  variant,
}: {
  feature: FeatureSummary;
  maxValue: number;
  variant: Variant;
}) {
  const value = variant === "praised" ? feature.positive : feature.negative;
  const widthPct = Math.max(4, Math.round((value / maxValue) * 100));
  const bar = variant === "praised" ? "bg-emerald-500" : "bg-red-500";
  return (
    <div className="grid grid-cols-[1fr_auto_auto] items-center gap-x-4 px-3 py-2.5">
      <p className="truncate text-sm font-medium text-zinc-800">{feature.name}</p>
      <p className="font-mono text-sm font-medium tabular-nums text-zinc-700">
        {feature.rating.toFixed(2)}/5
      </p>
      <p className="font-mono text-sm font-semibold tabular-nums text-zinc-900">
        {value}
        <span className="ml-1 text-xs font-normal text-zinc-500">of {feature.mentions}</span>
      </p>
      <div className="col-span-3 h-1.5 overflow-hidden rounded-full bg-zinc-100">
        <div
          className={`${bar} h-full rounded-full transition-[width]`}
          style={{ width: `${widthPct}%` }}
        />
      </div>
    </div>
  );
}
