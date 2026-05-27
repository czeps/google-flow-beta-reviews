"use client";

import { Star, ThumbsUp } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ratingTextColor } from "@/lib/colors";
import type { ReviewCard as ReviewCardData } from "@/lib/types";

const MAX_CHARS_COLLAPSED = 320;

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export function ReviewCard({ review }: { review: ReviewCardData }) {
  const [expanded, setExpanded] = useState(false);
  const long = review.body_en.length > MAX_CHARS_COLLAPSED;
  const text =
    expanded || !long
      ? review.body_en
      : `${review.body_en.slice(0, MAX_CHARS_COLLAPSED).trimEnd()}…`;

  return (
    <div className="space-y-2 rounded-xl border border-zinc-200/80 bg-white p-3">
      <div className="flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-1.5">
          <Star className={`size-3.5 fill-current ${ratingTextColor(review.rating)}`} />
          <span className={`font-mono font-semibold tabular-nums ${ratingTextColor(review.rating)}`}>
            {review.rating.toFixed(0)}
          </span>
          <span className="text-zinc-400">·</span>
          <span className="text-zinc-500">{formatDate(review.date)}</span>
        </div>
        <div className="flex items-center gap-2 text-zinc-500">
          {review.country && (
            <Badge variant="outline" className="text-[10px] uppercase">
              {review.country}
            </Badge>
          )}
          <Badge variant="ghost" className="font-mono text-[10px] lowercase">
            {review.lang}
          </Badge>
          {review.thumbs > 0 && (
            <span className="inline-flex items-center gap-1 font-mono tabular-nums">
              <ThumbsUp className="size-3" />
              {review.thumbs}
            </span>
          )}
        </div>
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-800">
        {text}
      </p>
      {long && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-xs font-medium text-sky-700 hover:text-sky-800"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}
