"use client";

import { CartesianGrid, Scatter, ScatterChart, XAxis, YAxis, ZAxis } from "recharts";
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
import type { DailyPoint } from "@/lib/types";

const config: ChartConfig = {
  avg: { label: "Avg score", color: "#3b82f6" },
  count: { label: "Reviews", color: "#3b82f6" },
};

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function DailyTrends({ data }: { data: DailyPoint[] }) {
  const chartData = data.map((d) => ({
    x: new Date(d.date).getTime(),
    y: d.avg,
    z: d.count,
    date: d.date,
  }));

  return (
    <Card className="rounded-2xl border-zinc-200/80 shadow-none">
      <CardHeader>
        <CardTitle className="text-base font-semibold">Daily trends</CardTitle>
        <CardDescription>Average score per day · dot size = review volume</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config} className="aspect-auto h-[260px] w-full">
          <ScatterChart margin={{ top: 10, right: 24, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e4e4e7" />
            <XAxis
              dataKey="x"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v) => formatDate(new Date(v).toISOString())}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
            />
            <YAxis
              dataKey="y"
              type="number"
              domain={[1, 5]}
              ticks={[1, 2, 3, 4, 5]}
              tickLine={false}
              axisLine={false}
              width={28}
            />
            <ZAxis dataKey="z" type="number" range={[64, 400]} />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  formatter={(value, name, item) => {
                    if (name === "y") return [`${(value as number).toFixed(2)} avg`];
                    if (name === "z") return [`${value} reviews`];
                    return [String(value)];
                  }}
                  labelFormatter={(_, payload) => {
                    const p = payload?.[0]?.payload as { date?: string } | undefined;
                    return p?.date ? formatDate(p.date) : "";
                  }}
                />
              }
            />
            <Scatter data={chartData} fill="#3b82f6" fillOpacity={0.85} />
          </ScatterChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
