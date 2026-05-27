"use client";

import { useState } from "react";
import { DailyTrends } from "./daily-trends";
import { FeatureList } from "./feature-list";
import { Header } from "./header";
import { KpiRow } from "./kpi-row";
import { ScoreDistribution } from "./score-distribution";
import type { DashboardData } from "@/lib/types";

export function Dashboard({ data }: { data: DashboardData }) {
  const [country, setCountry] = useState<string>("all");
  const slice = data.slices[country] ?? data.slices.all;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6 sm:p-8">
      <Header
        title="Google Flow Beta — Review Insights"
        source={data.source.label}
        country={country}
        countries={data.countries}
        onCountryChange={setCountry}
      />

      <KpiRow slice={slice} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ScoreDistribution data={slice.scores} />
        <DailyTrends data={slice.daily} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <FeatureList
          title="Most appreciated features"
          description="Ranked by positive mentions · click a row for reviews"
          features={slice.praised}
          variant="praised"
          reviewsByFeature={slice.reviewsByFeature}
        />
        <FeatureList
          title="Top issues to fix"
          description="Ranked by negative mentions · click a row for reviews"
          features={slice.issues}
          variant="issue"
          reviewsByFeature={slice.reviewsByFeature}
        />
      </div>
    </div>
  );
}
