"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CollectionRatePoint } from "@/lib/api/types";
import { format } from "date-fns";

interface CollectionRateChartProps {
  data: CollectionRatePoint[];
}

export function CollectionRateChart({ data }: CollectionRateChartProps) {
  const formatted = data.map((p) => ({
    ...p,
    label: format(new Date(p.date), "dd MMM"),
    ratePct: Math.round(p.rate * 100),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Collection Rate Over Time</CardTitle>
      </CardHeader>
      <CardContent className="pl-2">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={formatted} margin={{ top: 5, right: 12, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="label"
              stroke="hsl(var(--muted-foreground))"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              interval={Math.floor(formatted.length / 6)}
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
              formatter={(value) => [`${value}%`, "Rate"]}
            />
            <Line
              type="monotone"
              dataKey="ratePct"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
