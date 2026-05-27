"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FeatureRow } from "./feature-row";
import { ReviewDrawer } from "./review-drawer";
import type { FeatureSummary, ReviewCard as ReviewCardData } from "@/lib/types";

type Variant = "praised" | "issue";

export function FeatureList({
  title,
  description,
  features,
  variant,
  reviewsByFeature,
}: {
  title: string;
  description: string;
  features: FeatureSummary[];
  variant: Variant;
  reviewsByFeature: Record<string, ReviewCardData[]>;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const valueOf = (f: FeatureSummary) =>
    variant === "praised" ? f.positive : f.negative;
  const maxValue = features.reduce((m, f) => Math.max(m, valueOf(f)), 1);

  const selected = features.find((f) => f.id === selectedId) ?? null;
  const drawerKey = selected
    ? `${selected.id}:${variant === "praised" ? "positive" : "negative"}`
    : "";
  const drawerReviews = selected ? (reviewsByFeature[drawerKey] ?? []) : [];

  return (
    <Card className="rounded-2xl border-zinc-200/80 shadow-none">
      <CardHeader>
        <CardTitle className="text-base font-semibold">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {features.length === 0 ? (
          <p className="text-sm text-zinc-500">No themes met the threshold for this slice.</p>
        ) : (
          <ul className="divide-y divide-zinc-100">
            {features.map((f) => (
              <li key={f.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(f.id)}
                  className="w-full rounded-md text-left transition-colors hover:bg-zinc-50 focus-visible:bg-zinc-50 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-sky-500"
                >
                  <FeatureRow feature={f} maxValue={maxValue} variant={variant} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
      <ReviewDrawer
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedId(null);
        }}
        feature={selected}
        reviews={drawerReviews}
        variant={variant}
      />
    </Card>
  );
}
