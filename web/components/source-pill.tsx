import { Store } from "lucide-react";

export function SourcePill({ label }: { label: string }) {
  return (
    <span className="inline-flex h-9 items-center gap-2 rounded-full border border-sky-200 bg-sky-50/60 px-4 text-sm font-medium text-sky-700">
      <Store className="size-4" />
      {label}
    </span>
  );
}
