import type { BehavioralAnalysis, RiskAction, RiskLevel } from '../types';

const featureKeys: (keyof Omit<BehavioralAnalysis, 'sessionId' | 'analysisWindows' | 'consecutiveAnomalousWindows' | 'monitoringActive' | 'currentWindowAssessment'>)[] = [
  'typingRate',
  'dwellTime',
  'ppLatency',
  'rpLatency',
  'pauseRhythm',
  'rolloverRatio',
  'mouseVelocity',
  'mousePathLength',
  'mouseDisplacement',
  'directionChangeRate',
  'straightness',
  'clickInterval',
];

export function calculateBehaviorRiskScore(behavior: BehavioralAnalysis): number {
  const significant = featureKeys.filter((key) => behavior[key] === 'Significant Deviation').length;
  const slight = featureKeys.filter((key) => behavior[key] === 'Slight Deviation').length;
  const sustainedWindows = Math.max(0, behavior.consecutiveAnomalousWindows - 1);
  const anomalyWindows = behavior.analysisWindows.filter((window) => window === 'Anomalous').length;
  const hasHighRiskEvidence = significant >= 3 && anomalyWindows >= 2 && sustainedWindows >= 1;
  const rawScore = 15 + significant * 16 + slight * 5 + anomalyWindows * 8 + sustainedWindows * 10;

  return hasHighRiskEvidence ? Math.min(100, rawScore) : Math.min(69, rawScore);
}

export function riskLevelFromScore(score: number): RiskLevel {
  if (score >= 85) return 'CRITICAL';
  if (score >= 70) return 'VERY HIGH';
  if (score >= 50) return 'HIGH';
  if (score >= 25) return 'MEDIUM';
  return 'LOW';
}

export function riskActionForLevel(level: RiskLevel): RiskAction {
  const actions: Record<RiskLevel, RiskAction> = {
    LOW: 'Acceptable',
    MEDIUM: 'Monitor',
    HIGH: 'Step-up Re-authentication',
    'VERY HIGH': 'Loss of Privileges',
    CRITICAL: 'Freeze Account + Shadow Environment',
  };

  return actions[level];
}