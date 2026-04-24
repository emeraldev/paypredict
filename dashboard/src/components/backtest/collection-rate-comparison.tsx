"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_THEME } from "@/lib/constants";

interface CollectionRateComparisonProps {
  actualRate: number;
  projectedRate: number;
}

export function CollectionRateComparison({
  actualRate,
  projectedRate,
}: CollectionRateComparisonProps) {
  const data = [
    {
      label: "Current Rate",
      rate: Math.round(actualRate * 100),
      color: CHART_THEME.muted,
    },
    {
      label: "With PayPredict",
      rate: Math.round(projectedRate * 100),
      color: CHART_THEME.primary,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Collection Rate Impact</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} layout="vertical" margin={{ left: 100, right: 30 }}>
            <XAxis
              type="number"
              domain={[0, 100]}
              tick={{ fill: CHART_THEME.axis, fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
            />
            <YAxis
              type="category"
              dataKey="label"
              tick={{ fill: CHART_THEME.axis, fontSize: 12 }}
              width={100}
            />
            <Bar dataKey="rate" radius={[0, 6, 6, 0]} barSize={36}>
              {data.map((entry) => (
                <Cell key={entry.label} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
