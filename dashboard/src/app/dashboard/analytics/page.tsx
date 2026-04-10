import { AnalyticsStatCards } from "@/components/analytics/analytics-stat-cards";
import { CollectionRateChart } from "@/components/analytics/collection-rate-chart";
import { FailureFactorsChart } from "@/components/analytics/failure-factors-chart";
import { PredictionAccuracyChart } from "@/components/analytics/prediction-accuracy-chart";
import { RiskDistributionChart } from "@/components/analytics/risk-distribution-chart";
import { PageHeader } from "@/components/shared/page-header";
import {
  mockAnalyticsSummary,
  mockCollectionRate,
  mockFactorContributions,
} from "@/lib/mock-data";

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        description="Collection rates, prediction accuracy, and factor contributions over the last 30 days"
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CollectionRateChart data={mockCollectionRate} />
        <RiskDistributionChart data={mockAnalyticsSummary.risk_distribution} />
        <PredictionAccuracyChart data={mockAnalyticsSummary.prediction_accuracy} />
        <FailureFactorsChart data={mockFactorContributions} />
      </div>

      <AnalyticsStatCards summary={mockAnalyticsSummary} />
    </div>
  );
}
