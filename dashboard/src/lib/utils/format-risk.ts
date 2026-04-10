import { RISK_CONFIG, RISK_THRESHOLDS } from "@/lib/constants";

export type RiskLevel = "HIGH" | "MEDIUM" | "LOW";

export function getRiskConfig(level: RiskLevel) {
  return RISK_CONFIG[level];
}

export function scoreToRiskLevel(displayScore: number): RiskLevel {
  if (displayScore > RISK_THRESHOLDS.MEDIUM_MAX) return "HIGH";
  if (displayScore > RISK_THRESHOLDS.LOW_MAX) return "MEDIUM";
  return "LOW";
}

// Convert 0.0-1.0 float to 0-100 display score
export function displayScore(score: number): number {
  return Math.round(score * 100);
}

// Color logic for individual factor bars (0.0-1.0 raw score)
export function getFactorBarColor(rawScore: number): string {
  if (rawScore >= 0.61) return RISK_CONFIG.HIGH.barColor;
  if (rawScore >= 0.31) return RISK_CONFIG.MEDIUM.barColor;
  return RISK_CONFIG.LOW.barColor;
}
