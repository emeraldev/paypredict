"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_THEME } from "@/lib/constants";

interface PredictionAccuracyChartProps {
  data: {
    high_risk_actually_failed: number;
    low_risk_actually_succeeded: number;
  };
}

export function PredictionAccuracyChart({ data }: PredictionAccuracyChartProps) {
  const chartData = [
    {
      label: "High → Failed",
      accuracy: Math.round(data.high_risk_actually_failed * 100),
      color: CHART_THEME.high,
    },
    {
      label: "Low → Succeeded",
      accuracy: Math.round(data.low_risk_actually_succeeded * 100),
      color: CHART_THEME.low,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Prediction Accuracy</CardTitle>
      </CardHeader>
      <CardContent className="pl-2">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 5, right: 12, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
            <XAxis
              dataKey="label"
              tick={{ fill: CHART_THEME.axis, fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: CHART_THEME.grid }}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: CHART_THEME.axis, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
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
              formatter={(value) => [`${value}%`, "Accuracy"]}
            />
            <Bar dataKey="accuracy" radius={[6, 6, 0, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.label} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
