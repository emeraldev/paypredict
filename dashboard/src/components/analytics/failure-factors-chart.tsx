"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FACTOR_LABELS, RISK_CONFIG } from "@/lib/constants";
import type { FactorContribution } from "@/lib/api/types";

interface FailureFactorsChartProps {
  data: FactorContribution[];
}

export function FailureFactorsChart({ data }: FailureFactorsChartProps) {
  const chartData = [...data]
    .sort((a, b) => b.contribution - a.contribution)
    .map((d) => ({
      ...d,
      label: FACTOR_LABELS[d.factor] ?? d.factor,
      pct: Math.round(d.contribution * 100),
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Top Failure Contributors</CardTitle>
      </CardHeader>
      <CardContent className="pl-2">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 12, left: 100, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
            <XAxis
              type="number"
              stroke="hsl(var(--muted-foreground))"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <YAxis
              type="category"
              dataKey="label"
              stroke="hsl(var(--muted-foreground))"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={100}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              formatter={(value) => [`${value}%`, "Contribution"]}
            />
            <Bar dataKey="pct" fill={RISK_CONFIG.HIGH.barColor} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
