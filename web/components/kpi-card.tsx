import { Card, CardContent } from "@/components/ui/card";

export function KpiCard({
  label,
  value,
  subtitle,
}: {
  label: string;
  value: string;
  subtitle: string;
}) {
  return (
    <Card className="rounded-2xl border-zinc-200/80 shadow-none">
      <CardContent className="px-6">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
          {label}
        </p>
        <p className="mt-2 font-mono text-[34px] font-semibold leading-none text-zinc-900 tabular-nums">
          {value}
        </p>
        <p className="mt-3 text-xs text-zinc-500">{subtitle}</p>
      </CardContent>
    </Card>
  );
}
