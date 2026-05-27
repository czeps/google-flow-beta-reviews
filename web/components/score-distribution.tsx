"use client";

import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from "recharts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { ScoreBin } from "@/lib/types";

const COLORS: Record<number, string> = {
  1: "#ef4444",
  2: "#f97316",
  3: "#eab308",
  4: "#84cc16",
  5: "#10b981",
};

const config: ChartConfig = {
  count: { label: "Reviews", color: "#3b82f6" },
};

export function ScoreDistribution({ data }: { data: ScoreBin[] }) {
  const chartData = data.map((d) => ({ score: `${d.score}★`, count: d.count, fill: COLORS[d.score] }));
  return (
    <Card className="rounded-2xl border-zinc-200/80 shadow-none">
      <CardHeader>
        <CardTitle className="text-base font-semibold">Score distribution</CardTitle>
        <CardDescription>Reviews per star rating</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config} className="aspect-auto h-[260px] w-full">
          <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#e4e4e7" />
            <XAxis dataKey="score" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={28} />
            <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
            <Bar dataKey="count" radius={[6, 6, 0, 0]}>
              {chartData.map((d) => (
                <Cell key={d.score} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
