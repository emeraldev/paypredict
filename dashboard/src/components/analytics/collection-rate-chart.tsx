"use client";

import { format } from "date-fns";
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
import { CHART_THEME } from "@/lib/constants";

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
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
            <XAxis
              dataKey="label"
              tick={{ fill: CHART_THEME.axis, fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: CHART_THEME.grid }}
              interval={Math.max(0, Math.floor(formatted.length / 6))}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: CHART_THEME.axis, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: CHART_THEME.tooltipBg,
                border: `1px solid ${CHART_THEME.tooltipBorder}`,
                borderRadius: "8px",
                color: CHART_THEME.tooltipText,
                fontSize: "12px",
              }}
              labelStyle={{ color: CHART_THEME.tooltipText }}
              itemStyle={{ color: CHART_THEME.tooltipText }}
              formatter={(value) => [`${value}%`, "Rate"]}
            />
            <Line
              type="monotone"
              dataKey="ratePct"
              stroke={CHART_THEME.primary}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: CHART_THEME.primary }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
