export type AccountStatus = 'Active' | 'Frozen' | 'Restricted';
export type EnrollmentStatus = 'Enrolled' | 'Partially Enrolled' | 'Not Enrolled';
export const riskLevels = ['LOW', 'MEDIUM', 'HIGH', 'VERY HIGH', 'CRITICAL'] as const;
export type RiskLevel = (typeof riskLevels)[number];
export type RiskAction =
  | 'Acceptable'
  | 'Monitor'
  | 'Step-up Re-authentication'
  | 'Loss of Privileges'
  | 'Freeze Account + Shadow Environment';
export type DeviceStatus = 'Approved' | 'Pending' | 'Denied' | 'Blocked';
export type SessionLifecycle = 'active' | 'newly_created' | 'destroyed';
export type SessionStatus =
  | 'Normal'
  | 'Monitoring'
  | 'Suspicious'
  | 'Re-authentication Required'
  | 'Restricted'
  | 'Frozen'
  | 'Terminated';
export type AlertState =
  | RiskLevel
  | 'Suspicious'
  | 'Re-authentication Required'
  | 'Restricted'
  | 'Frozen';
export type FeatureState = 'Normal' | 'Slight Deviation' | 'Significant Deviation';
export type DeviationLevel = 'Low' | 'Mild' | 'Moderate' | 'High';
export type CurrentResponse =
  | RiskAction
  | 'None';

export interface Employee {
  id: string;
  name: string;
  department: string;
  role: string;
  accountStatus: AccountStatus;
  enrollmentStatus: EnrollmentStatus;
  registeredDevices: number;
  activeSessions: number;
  currentRisk: RiskLevel;
  lastAuthentication: string;
  lastActivity: string;
  lastAnalysis: string;
  enrolledDeviceId?: string;
}

export interface Device {
  id: string;
  employeeId: string;
  browser: string;
  firstRegistered?: string;
  lastSeen?: string;
  status: DeviceStatus;
  verificationStatus: string;
  sessionIp?: string;
  risk?: RiskLevel;
  riskScore?: number;
  currentSession?: string;
}

export interface Session {
  id: string;
  employeeId: string;
  deviceId: string;
  loginTime: string;
  duration: string;
  sessionIp: string;
  riskScore: number;
  riskState: RiskLevel;
  status: SessionStatus;
  currentResponse: CurrentResponse;
  lifecycle: SessionLifecycle;
  createdTime: string;
  initialRisk?: RiskLevel;
  destroyedTime?: string;
  terminationReason?: string;
  shadowEnvironment?: ShadowEnvironment;
  stepUpTriggered?: boolean;
}

export interface ShadowEnvironment {
  active: boolean;
  triggerTime?: string;
  reason?: string;
  status?: string;
}

export interface BehavioralAnalysis {
  sessionId: string;
  typingRate: FeatureState;
  dwellTime: FeatureState;
  ppLatency: FeatureState;
  rpLatency: FeatureState;
  pauseRhythm: FeatureState;
  rolloverRatio: FeatureState;
  mouseVelocity: FeatureState;
  mousePathLength: FeatureState;
  mouseDisplacement: FeatureState;
  directionChangeRate: FeatureState;
  straightness: FeatureState;
  clickInterval: FeatureState;
  analysisWindows: ('Normal' | 'Anomalous')[];
  consecutiveAnomalousWindows: number;
  monitoringActive: boolean;
  currentWindowAssessment: 'Normal' | 'Anomalous';
}

export interface Alert {
  id: string;
  employeeId: string;
  sessionId: string;
  riskScore: number;
  state: AlertState;
  trigger: string;
  timestamp: string;
  status: 'Open' | 'Investigating' | 'Resolved';
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  event: string;
  target: string;
  action: string;
  result: 'Success' | 'Failed';
  details: string;
}

export interface SecurityReport {
  id: string;
  employeeId: string;
  deviceId: string;
  sessionId: string;
  generatedAt: string;
  department: string;
  currentSessionStatus: string;
  riskScore: number;
  riskState: RiskLevel;
  anomalousWindowCount: number;
  consecutiveAnomalousWindows: number;
  currentResponse: string;
  riskTrend: { time: string; score: number }[];
  behavioralTimeline: { time: string; state: string }[];
  keyboardTrend: {
    time: string;
    typingRate: number;
    dwellTime: number;
    ppLatency: number;
    rpLatency: number;
    pauseRhythm: number;
  }[];
  mouseTrend: {
    time: string;
    velocity: number;
    pathLength: number;
    directionChange: number;
    straightness: number;
    clickInterval: number;
  }[];
  profileComparison: {
    feature: string;
    baseline: string;
    current: string;
    deviation: DeviationLevel;
  }[];
  continuousTimeline: { time: string; event: string }[];
  securityEvents: string[];
  overallAssessment: string;
}

export interface SecurityEvent {
  id: string;
  message: string;
  time: string;
}
