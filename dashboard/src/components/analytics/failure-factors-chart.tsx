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
import type { FactorContribution } from "@/lib/api/types";
import { CHART_THEME, FACTOR_LABELS } from "@/lib/constants";

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
            margin={{ top: 5, right: 20, left: 140, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={CHART_THEME.grid}
              horizontal={false}
            />
            <XAxis
              type="number"
              tick={{ fill: CHART_THEME.axis, fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: CHART_THEME.grid }}
              tickFormatter={(v) => `${v}%`}
            />
            <YAxis
              type="category"
              dataKey="label"
              tick={{ fill: CHART_THEME.axis, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={130}
            />
            <Tooltip
              cursor={{ fill: CHART_THEME.muted }}
              contentStyle={{
                backgroundColor: CHART_THEME.tooltipBg,
                border: `1px solid ${CHART_THEME.tooltipBorder}`,
                borderRadius: "8px",
                color: CHART_THEME.tooltipText,
                fontSize: "12px",
              }}
              labelStyle={{ color: CHART_THEME.tooltipText }}
              itemStyle={{ color: CHART_THEME.tooltipText }}
              formatter={(value) => [`${value}%`, "Contribution"]}
            />
            <Bar dataKey="pct" fill={CHART_THEME.high} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
