"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RISK_CONFIG } from "@/lib/constants";

interface RiskDistributionChartProps {
  data: {
    high: number;
    medium: number;
    low: number;
  };
}

export function RiskDistributionChart({ data }: RiskDistributionChartProps) {
  const chartData = [
    { name: "High", value: data.high, color: RISK_CONFIG.HIGH.barColor },
    { name: "Medium", value: data.medium, color: RISK_CONFIG.MEDIUM.barColor },
    { name: "Low", value: data.low, color: RISK_CONFIG.LOW.barColor },
  ];
  const total = data.high + data.medium + data.low;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Risk Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          <ResponsiveContainer width="50%" height={220}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
              >
                {chartData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex-1 space-y-3">
            {chartData.map((item) => {
              const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
              return (
                <div key={item.name} className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-3 w-3 rounded-sm"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-sm font-medium">{item.name}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium tabular-nums">
                      {item.value.toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground">{pct}%</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
