"""Pydantic schemas for the dashboard analytics endpoints."""
from decimal import Decimal

from pydantic import BaseModel


# ---- GET /v1/analytics/summary ----

class PredictionAccuracy(BaseModel):
    high_risk_failure_rate: float
    low_risk_success_rate: float
    overall_accuracy: float


class RiskDistribution(BaseModel):
    high: int
    medium: int
    low: int


class AnalyticsSummaryResponse(BaseModel):
    period: str
    total_scored: int
    total_outcomes: int
    collection_rate: float
    collection_rate_change: float
    risk_distribution: RiskDistribution
    prediction_accuracy: PredictionAccuracy
    total_value_scored: Decimal
    total_value_at_risk: Decimal
    avg_score: float
    outcomes_reporting_rate: float


# ---- GET /v1/analytics/collection-rate ----

class CollectionRatePoint(BaseModel):
    date: str
    collection_rate: float
    scored_count: int
    failed_count: int


class CollectionRateResponse(BaseModel):
    data_points: list[CollectionRatePoint]


# ---- GET /v1/analytics/factors ----

class FactorContributionItem(BaseModel):
    factor: str
    avg_contribution: float
    correlation_with_failure: float


class FactorsResponse(BaseModel):
    factors: list[FactorContributionItem]


# ---- GET /v1/analytics/accuracy ----

class ConfusionMatrix(BaseModel):
    predicted_high_actual_failed: int
    predicted_high_actual_success: int
    predicted_medium_actual_failed: int
    predicted_medium_actual_success: int
    predicted_low_actual_failed: int
    predicted_low_actual_success: int


class AccuracyResponse(BaseModel):
    confusion_matrix: ConfusionMatrix
