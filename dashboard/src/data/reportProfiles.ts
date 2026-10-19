import type { Device, Employee, RiskLevel, SecurityReport, Session } from '../types';

export function buildEmployeeSecurityReport(
  employee: Employee,
  device: Device & { risk: RiskLevel; riskScore: number },
  session: Session | undefined,
  generatedAt: string,
): Omit<SecurityReport, 'id'> {
  const isHighSignal = ['HIGH', 'VERY HIGH', 'CRITICAL'].includes(device.risk);
  const isMedium = device.risk === 'MEDIUM';
  const sessionId = session?.id ?? '—';
  const currentScore = session?.riskScore ?? device.riskScore;

  const riskTrend = isHighSignal
    ? [
        { time: '09:00', score: 28 },
        { time: '09:30', score: 32 },
        { time: '10:00', score: 45 },
        { time: '10:15', score: 58 },
        { time: '10:30', score: 72 },
        { time: '10:45', score: currentScore },
      ]
    : isMedium
      ? [
          { time: '09:00', score: 22 },
          { time: '09:30', score: 28 },
          { time: '10:00', score: 35 },
          { time: '10:15', score: 42 },
          { time: '10:30', score: 48 },
          { time: '10:45', score: currentScore },
        ]
      : [
          { time: '09:00', score: 18 },
          { time: '09:15', score: 20 },
          { time: '09:30', score: 22 },
          { time: '09:45', score: 19 },
          { time: '10:00', score: 24 },
          { time: '10:15', score: currentScore },
        ];

  const behavioralTimeline = isHighSignal
    ? [
        { time: '09:00', state: 'Normal' },
        { time: '09:15', state: 'Normal' },
        { time: '09:30', state: 'Mild Deviation' },
        { time: '09:45', state: 'Normal' },
        { time: '10:00', state: 'Mild Deviation' },
        { time: '10:15', state: 'Normal' },
        { time: '10:30', state: 'Significant Deviation' },
      ]
    : [
        { time: '09:00', state: 'Normal' },
        { time: '09:15', state: 'Normal' },
        { time: '09:30', state: 'Mild Deviation' },
        { time: '09:45', state: 'Normal' },
        { time: '10:00', state: 'Mild Deviation' },
        { time: '10:15', state: 'Normal' },
      ];

  const keyboardTrend = [
    { time: '09:00', typingRate: 61, dwellTime: 116, ppLatency: 142, rpLatency: 98, pauseRhythm: 0.42 },
    { time: '09:30', typingRate: 63, dwellTime: 118, ppLatency: 138, rpLatency: 96, pauseRhythm: 0.41 },
    { time: '10:00', typingRate: 59, dwellTime: 122, ppLatency: 155, rpLatency: 102, pauseRhythm: 0.48 },
    { time: '10:30', typingRate: 57, dwellTime: 124, ppLatency: 168, rpLatency: 108, pauseRhythm: 0.52 },
  ];

  const mouseTrend = [
    { time: '09:00', velocity: 405, pathLength: 820, directionChange: 0.29, straightness: 0.71, clickInterval: 540 },
    { time: '09:30', velocity: 412, pathLength: 835, directionChange: 0.31, straightness: 0.69, clickInterval: 528 },
    { time: '10:00', velocity: 428, pathLength: 860, directionChange: 0.36, straightness: 0.66, clickInterval: 512 },
    { time: '10:30', velocity: 435, pathLength: 890, directionChange: 0.47, straightness: 0.61, clickInterval: 498 },
  ];

  const profileComparison = isHighSignal
    ? [
        { feature: 'Typing Rate', baseline: '62 WPM', current: '57 WPM', deviation: 'Mild' as const },
        { feature: 'Dwell Time', baseline: '118 ms', current: '124 ms', deviation: 'Mild' as const },
        { feature: 'Press-to-Press Latency', baseline: '140 ms', current: '168 ms', deviation: 'Moderate' as const },
        { feature: 'Mouse Velocity', baseline: '410 px/s', current: '435 px/s', deviation: 'Low' as const },
        { feature: 'Direction Changes', baseline: '0.31', current: '0.47', deviation: 'Moderate' as const },
      ]
    : [
        { feature: 'Typing Rate', baseline: '62 WPM', current: '59 WPM', deviation: 'Mild' as const },
        { feature: 'Dwell Time', baseline: '118 ms', current: '121 ms', deviation: 'Low' as const },
        { feature: 'Mouse Velocity', baseline: '410 px/s', current: '418 px/s', deviation: 'Low' as const },
        { feature: 'Direction Changes', baseline: '0.31', current: '0.34', deviation: 'Low' as const },
      ];

  const continuousTimeline = isHighSignal
    ? [
        { time: '09:00', event: 'Session authenticated — behavioral monitoring active' },
        { time: '09:10', event: 'Continuous analysis windows running within protected session' },
        { time: '09:30', event: 'Mild behavioral deviation observed — within expected natural variation' },
        { time: '09:45', event: 'Behavior returned toward established baseline' },
        { time: '10:05', event: 'Significant deviation detected across keyboard rhythm features' },
        { time: '10:07', event: 'Risk classification increased per AI Risk Engine assessment' },
        { time: '10:08', event: 'Step-up authentication triggered by policy threshold' },
      ]
    : [
        { time: '09:00', event: 'Session authenticated — behavioral monitoring active' },
        { time: '09:30', event: 'Mild fluctuation in typing rhythm — classified as normal variation' },
        { time: '10:00', event: 'Behavioral state returned to baseline profile envelope' },
        { time: '10:15', event: 'Session remains within acceptable continuous authentication bounds' },
      ];

  const securityEvents = isHighSignal
    ? [
        'Behavioral anomaly detected',
        'Risk classification changed',
        'Step-up authentication triggered',
        'New device pending approval (contextual)',
        ...(session?.status === 'Restricted' ? ['Session restricted'] : []),
        ...(session?.shadowEnvironment?.active ? ['Shadow Environment / Deception Router activation'] : []),
      ]
    : ['Behavioral monitoring active', 'Risk classification within normal operational band'];

  const overallAssessment = isHighSignal
    ? 'The session remained broadly consistent with the employee\'s established behavioral profile during early observation windows. Minor fluctuations were observed and did not independently result in a high-risk classification. A later sustained deviation across keyboard timing features contributed to an elevated risk classification and triggered the configured step-up authentication response. Evidence reflects derived behavioral features only — not content surveillance.'
    : 'Observed keyboard and mouse features remained largely aligned with the enrolled behavioral profile throughout the monitored period. Mild, short-lived deviations were treated as natural human variation rather than sustained anomaly. No escalation to restrictive controls was warranted based on available continuous authentication evidence.';

  return {
    employeeId: employee.id,
    deviceId: device.id,
    sessionId,
    generatedAt,
    department: employee.department,
    currentSessionStatus: session?.status ?? 'No active session',
    riskScore: currentScore,
    riskState: device.risk,
    anomalousWindowCount: isHighSignal ? 3 : isMedium ? 1 : 0,
    consecutiveAnomalousWindows: isHighSignal ? 2 : isMedium ? 1 : 0,
    currentResponse: session?.currentResponse ?? 'Monitor',
    riskTrend,
    behavioralTimeline,
    keyboardTrend,
    mouseTrend,
    profileComparison,
    continuousTimeline,
    securityEvents,
    overallAssessment,
  };
}
