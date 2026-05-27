"use client";

import { useMemo } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ReviewCard } from "./review-card";
import type { FeatureSummary, ReviewCard as ReviewCardData } from "@/lib/types";

type Variant = "praised" | "issue";

export function ReviewDrawer({
  open,
  onOpenChange,
  feature,
  reviews,
  variant,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  feature: FeatureSummary | null;
  reviews: ReviewCardData[];
  variant: Variant;
}) {
  const summary = useMemo(() => {
    if (!feature || reviews.length === 0) return null;
    const countries = new Set(reviews.map((r) => r.country).filter(Boolean));
    const ratings = reviews.map((r) => r.rating).filter((n) => Number.isFinite(n));
    const avg =
      ratings.length > 0
        ? Number((ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(2))
        : 0;
    return {
      kind: variant === "praised" ? "positive" : "negative",
      count: reviews.length,
      countries: countries.size,
      avg,
    };
  }, [feature, reviews, variant]);

  const accentClass =
    variant === "praised" ? "text-emerald-700" : "text-red-700";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
        <SheetHeader className="border-b border-zinc-200/80 px-5 py-4">
          <SheetTitle className="text-base font-semibold">
            {feature?.name ?? "Reviews"}
          </SheetTitle>
          {feature && (
            <SheetDescription className="text-xs text-zinc-500">
              {feature.description}
            </SheetDescription>
          )}
          {summary && (
            <p className={`mt-2 text-xs font-medium ${accentClass}`}>
              {summary.count} {summary.kind} mention{summary.count === 1 ? "" : "s"}
              {summary.countries > 0 ? ` · ${summary.countries} ${summary.countries === 1 ? "country" : "countries"}` : ""}
              {summary.avg ? ` · ${summary.avg.toFixed(2)} avg ★` : ""}
            </p>
          )}
        </SheetHeader>
        <ScrollArea className="min-h-0 flex-1">
          <div className="space-y-2 px-5 py-4">
            {reviews.length === 0 ? (
              <p className="py-8 text-center text-sm text-zinc-500">
                No reviews for this slice.
              </p>
            ) : (
              reviews.map((r) => <ReviewCard key={r.id} review={r} />)
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
