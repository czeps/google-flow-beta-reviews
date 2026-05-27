// Sentiment colour scale matching the reference dashboard.
// Returns Tailwind class names rather than raw hex so the design stays themable.

export function barColor(rating: number): string {
  if (rating >= 4.5) return "bg-emerald-500";
  if (rating >= 3.5) return "bg-lime-500";
  if (rating >= 3.0) return "bg-amber-500";
  if (rating >= 2.0) return "bg-orange-500";
  return "bg-red-500";
}

export function ratingTextColor(rating: number): string {
  if (rating >= 4.5) return "text-emerald-600";
  if (rating >= 3.5) return "text-lime-600";
  if (rating >= 3.0) return "text-amber-600";
  if (rating >= 2.0) return "text-orange-600";
  return "text-red-600";
}
