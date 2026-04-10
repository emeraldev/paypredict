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
import { RISK_CONFIG } from "@/lib/constants";

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
      color: RISK_CONFIG.HIGH.barColor,
    },
    {
      label: "Low → Succeeded",
      accuracy: Math.round(data.low_risk_actually_succeeded * 100),
      color: RISK_CONFIG.LOW.barColor,
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
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="label"
              stroke="hsl(var(--muted-foreground))"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, 100]}
              stroke="hsl(var(--muted-foreground))"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              formatter={(value) => [`${value}%`, "Accuracy"]}
            />
            <Bar dataKey="accuracy" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, i) => (
                <rect key={i} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
