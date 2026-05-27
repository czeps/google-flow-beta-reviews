"use client";

import { Globe } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";

type Country = { slug: string; label: string; count: number };

export function CountryFilter({
  value,
  options,
  onChange,
}: {
  value: string;
  options: Country[];
  onChange: (slug: string) => void;
}) {
  const selected = options.find((c) => c.slug === value) ?? options[0];

  return (
    <Select value={value} onValueChange={(v) => v && onChange(v)}>
      <SelectTrigger
        size="sm"
        className="h-9 rounded-full border-sky-200 bg-sky-50/60 px-4 text-sm font-medium text-sky-700 hover:bg-sky-100/60 focus:ring-sky-200 [&_svg]:text-sky-700"
      >
        <Globe className="size-4" />
        <span className="flex items-center gap-2">
          <span>{selected?.label ?? "Pick a country"}</span>
          <span className="font-mono text-xs tabular-nums opacity-70">
            {selected?.count ?? ""}
          </span>
        </span>
      </SelectTrigger>
      <SelectContent className="max-h-[420px]">
        {options.map((c) => (
          <SelectItem key={c.slug} value={c.slug}>
            <span className="flex w-full items-center justify-between gap-6">
              <span>{c.label}</span>
              <span className="font-mono text-xs tabular-nums text-zinc-500">
                {c.count}
              </span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
