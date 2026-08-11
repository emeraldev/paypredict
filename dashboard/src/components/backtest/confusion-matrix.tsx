import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BacktestConfusionMatrix as ConfusionMatrixType } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface ConfusionMatrixProps {
  data: ConfusionMatrixType;
}

function Cell({
  count,
  total,
  correct,
}: {
  count: number;
  total: number;
  correct: boolean;
}) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div
      className={cn(
        "rounded-lg p-4 text-center",
        correct ? "bg-risk-low-bg" : "bg-risk-high-bg",
      )}
    >
      <p className="text-2xl font-bold tabular-nums text-foreground">{count}</p>
      <p className="text-xs text-muted-foreground">{pct}%</p>
    </div>
  );
}

export function ConfusionMatrix({ data }: ConfusionMatrixProps) {
  const highTotal = data.predicted_high_actual_failed + data.predicted_high_actual_success;
  const medTotal = data.predicted_medium_actual_failed + data.predicted_medium_actual_success;
  const lowTotal = data.predicted_low_actual_failed + data.predicted_low_actual_success;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Prediction vs Reality</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-2">
          {/* Header row */}
          <div />
          <p className="text-center text-xs font-semibold text-muted-foreground">
            Actually Succeeded
          </p>
          <p className="text-center text-xs font-semibold text-muted-foreground">
            Actually Failed
          </p>

          {/* HIGH row */}
          <p className="flex items-center text-xs font-semibold text-risk-high-fg">
            Predicted HIGH
          </p>
          <Cell
            count={data.predicted_high_actual_success}
            total={highTotal}
            correct={false}
          />
          <Cell
            count={data.predicted_high_actual_failed}
            total={highTotal}
            correct={true}
          />

          {/* MEDIUM row */}
          <p className="flex items-center text-xs font-semibold text-risk-med-fg">
            Predicted MEDIUM
          </p>
          <Cell
            count={data.predicted_medium_actual_success}
            total={medTotal}
            correct={false}
          />
          <Cell
            count={data.predicted_medium_actual_failed}
            total={medTotal}
            correct={false}
          />

          {/* LOW row */}
          <p className="flex items-center text-xs font-semibold text-risk-low-fg">
            Predicted LOW
          </p>
          <Cell
            count={data.predicted_low_actual_success}
            total={lowTotal}
            correct={true}
          />
          <Cell
            count={data.predicted_low_actual_failed}
            total={lowTotal}
            correct={false}
          />
        </div>
      </CardContent>
    </Card>
  );
}
