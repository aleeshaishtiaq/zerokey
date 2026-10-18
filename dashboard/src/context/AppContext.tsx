import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { buildEmployeeSecurityReport } from '../data/reportProfiles';
import { isSupportedChromiumBrowser } from '../utils/browserSupport';
import { calculateBehaviorRiskScore, riskActionForLevel, riskLevelFromScore } from '../utils/riskAssessment';
import {
  behavioralBySession,
  initialAlerts,
  initialAuditEvents,
  initialDevices,
  initialEmployees,
  initialSecurityEvents,
  initialSessions,
} from '../data/mockData';
import type {
  Alert,
  AuditEvent,
  BehavioralAnalysis,
  Device,
  Employee,
  RiskLevel,
  SecurityEvent,
  SecurityReport,
  Session,
} from '../types';

function nowTimestamp() {
  return new Date().toLocaleString('en-US', {
    weekday: undefined,
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

function newAuditId() {
  return `AUD-${Date.now().toString(36).toUpperCase()}`;
}

interface AppContextValue {
  employees: Employee[];
  devices: Device[];
  sessions: Session[];
  alerts: Alert[];
  auditEvents: AuditEvent[];
  securityEvents: SecurityEvent[];
  behavioral: Record<string, BehavioralAnalysis>;
  reports: SecurityReport[];
  addAudit: (partial: Omit<AuditEvent, 'id' | 'timestamp'> & { timestamp?: string }) => void;
  approveDevice: (deviceId: string) => void;
  denyDevice: (deviceId: string) => void;
  removeDevice: (deviceId: string) => void;
  blockDevice: (deviceId: string) => void;
  unfreezeAccount: (employeeId: string) => void;
  triggerReauth: (sessionId: string) => void;
  restrictSession: (sessionId: string) => void;
  terminateSession: (sessionId: string) => void;
  activateShadow: (sessionId: string, reason: string) => void;
  generateReport: (employeeId: string) => SecurityReport[];
  getEmployee: (id: string) => Employee | undefined;
  getDevice: (id: string) => Device | undefined;
  getSession: (id: string) => Session | undefined;
  syncEmployeeCounts: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const initialRiskAdjustedSessions = initialSessions.map((session) => {
    const behavior = behavioralBySession[session.id];
    const riskScore = behavior ? calculateBehaviorRiskScore(behavior) : session.riskScore;
    const riskState = riskLevelFromScore(riskScore);
    const currentResponse = riskActionForLevel(riskState);
    const status = {
      LOW: 'Normal',
      MEDIUM: 'Monitoring',
      HIGH: 'Re-authentication Required',
      'VERY HIGH': 'Restricted',
      CRITICAL: 'Frozen',
    }[riskState] as Session['status'];

    return {
      ...session,
      riskScore,
      riskState,
      currentResponse,
      status,
      stepUpTriggered: riskState === 'HIGH',
      shadowEnvironment:
        riskState === 'CRITICAL'
          ? {
              ...session.shadowEnvironment,
              active: true,
              triggerTime: session.shadowEnvironment?.triggerTime ?? session.createdTime,
              reason: session.shadowEnvironment?.reason ?? 'Critical risk threshold reached',
              status: 'Deception Routing: Active',
            }
          : session.shadowEnvironment,
    };
  });
  const [employees, setEmployees] = useState(() =>
    initialEmployees.map((employee) =>
      initialRiskAdjustedSessions.some(
        (session) => session.employeeId === employee.id && session.riskState === 'CRITICAL',
      )
        ? { ...employee, accountStatus: 'Frozen' as const, currentRisk: 'CRITICAL' as const }
        : employee,
    ),
  );
  const [devices, setDevices] = useState(initialDevices);
  const [sessions, setSessions] = useState<Session[]>(initialRiskAdjustedSessions);
  const [alerts] = useState(initialAlerts);
  const [auditEvents, setAuditEvents] = useState(initialAuditEvents);
  const [securityEvents, setSecurityEvents] = useState(initialSecurityEvents);
  const [behavioral] = useState(behavioralBySession);
  const [reports, setReports] = useState<SecurityReport[]>([]);

  const addAudit = useCallback(
    (partial: Omit<AuditEvent, 'id' | 'timestamp'> & { timestamp?: string }) => {
      const entry: AuditEvent = {
        id: newAuditId(),
        timestamp: partial.timestamp ?? nowTimestamp(),
        event: partial.event,
        target: partial.target,
        action: partial.action,
        result: partial.result,
        details: partial.details,
      };
      setAuditEvents((prev) => [entry, ...prev]);
      setSecurityEvents((prev) => [
        {
          id: `SE-${Date.now()}`,
          message: `${partial.event} — ${partial.target}`,
          time: entry.timestamp.split(', ').pop() ?? entry.timestamp,
        },
        ...prev.slice(0, 19),
      ]);
    },
    [],
  );

  const syncEmployeeCounts = useCallback(() => {
    setEmployees((prev) =>
      prev.map((e) => ({
        ...e,
        registeredDevices: devices.filter(
          (d) => d.employeeId === e.id && d.status !== 'Denied',
        ).length,
        activeSessions: sessions.filter(
          (s) =>
            s.employeeId === e.id &&
            !['Terminated', 'Frozen'].includes(s.status) &&
            s.duration !== 'Terminated',
        ).length,
      })),
    );
  }, [devices, sessions]);

  useEffect(() => {
    syncEmployeeCounts();
  }, [devices, sessions, syncEmployeeCounts]);

  const getEmployee = useCallback((id: string) => employees.find((e) => e.id === id), [employees]);
  const getDevice = useCallback((id: string) => devices.find((d) => d.id === id), [devices]);
  const getSession = useCallback((id: string) => sessions.find((s) => s.id === id), [sessions]);

  const approveDevice = useCallback(
    (deviceId: string) => {
      const device = devices.find((d) => d.id === deviceId);
      if (!device || device.status !== 'Pending') return;
      const emp = employees.find((e) => e.id === device.employeeId);
      if (!isSupportedChromiumBrowser(device.browser)) {
        addAudit({
          event: 'Unsupported device rejected',
          target: emp?.name ?? device.employeeId,
          action: 'Rejected Device',
          result: 'Failed',
          details: `${device.browser} is not a supported Chromium-based browser.`,
        });
        return;
      }
      setDevices((prev) =>
        prev.map((d) =>
          d.id === deviceId
            ? {
                ...d,
                status: 'Approved',
                verificationStatus: 'Verified',
                firstRegistered: d.firstRegistered ?? nowTimestamp(),
                lastSeen: nowTimestamp(),
                risk: d.risk ?? 'LOW',
                riskScore: d.riskScore ?? 22,
              }
            : d,
        ),
      );
      addAudit({
        event: 'Device approved',
        target: emp?.name ?? device.employeeId,
        action: 'Accepted Device',
        result: 'Success',
        details: `Device ${device.id} accepted for ${emp?.name ?? 'employee'}.`,
      });
    },
    [devices, employees, addAudit],
  );

  const denyDevice = useCallback(
    (deviceId: string) => {
      const device = devices.find((d) => d.id === deviceId);
      if (!device || device.status !== 'Pending') return;
      const emp = employees.find((e) => e.id === device.employeeId);
      setDevices((prev) =>
        prev.map((d) =>
          d.id === deviceId
            ? {
                ...d,
                status: 'Denied',
                verificationStatus: 'Denied',
                firstRegistered: undefined,
                lastSeen: undefined,
                sessionIp: undefined,
                risk: undefined,
                riskScore: undefined,
              }
            : d,
        ),
      );
      addAudit({
        event: 'Device denied',
        target: emp?.name ?? device.employeeId,
        action: 'Denied Device',
        result: 'Success',
        details: 'Pending device connection denied.',
      });
    },
    [devices, employees, addAudit],
  );

  const removeDevice = useCallback(
    (deviceId: string) => {
      const device = devices.find((d) => d.id === deviceId);
      if (!device || device.status !== 'Approved') return;
      const emp = employees.find((e) => e.id === device.employeeId);
      setDevices((prev) => prev.filter((d) => d.id !== deviceId));
      addAudit({
        event: 'Device removed',
        target: emp?.name ?? device.employeeId,
        action: 'Removed Device',
        result: 'Success',
        details: 'Approved device removed.',
      });
    },
    [devices, employees, addAudit],
  );

  const blockDevice = useCallback(
    (deviceId: string) => {
      const device = devices.find((d) => d.id === deviceId);
      if (!device) return;
      const emp = employees.find((e) => e.id === device.employeeId);
      setDevices((prev) =>
        prev.map((d) =>
          d.id === deviceId ? { ...d, status: 'Blocked', verificationStatus: 'Blocked' } : d,
        ),
      );
      addAudit({
        event: 'Device blocked',
        target: emp?.name ?? device.employeeId,
        action: 'Blocked Device',
        result: 'Success',
        details: 'Device blocked from future sessions.',
      });
    },
    [devices, employees, addAudit],
  );

  const unfreezeAccount = useCallback(
    (employeeId: string) => {
      const emp = employees.find((e) => e.id === employeeId);
      setEmployees((prev) =>
        prev.map((e) =>
          e.id === employeeId ? { ...e, accountStatus: 'Active', currentRisk: 'LOW' } : e,
        ),
      );
      addAudit({
        event: 'Account unfrozen',
        target: emp?.name ?? employeeId,
        action: 'Account unfrozen',
        result: 'Success',
        details: 'Account restored to active status after security review.',
      });
    },
    [employees, addAudit],
  );

  const triggerReauth = useCallback(
    (sessionId: string) => {
      const session = sessions.find((s) => s.id === sessionId);
      const emp = session ? employees.find((e) => e.id === session.employeeId) : undefined;
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? {
                ...s,
                status: 'Re-authentication Required',
                riskState: 'HIGH',
                currentResponse: 'Step-up Re-authentication',
                stepUpTriggered: true,
              }
            : s,
        ),
      );
      if (session) {
        setEmployees((prev) =>
          prev.map((employee) =>
            employee.id === session.employeeId
              ? { ...employee, currentRisk: 'HIGH' }
              : employee,
          ),
        );
      }
      addAudit({
        event: 'Step-up authentication triggered',
        target: `${emp?.name ?? 'Unknown'} / ${sessionId}`,
        action: 'Step-up Re-authentication',
        result: 'Success',
        details: 'Step-up authentication triggered for session review.',
      });
    },
    [sessions, employees, addAudit],
  );

  const restrictSession = useCallback(
    (sessionId: string) => {
      const session = sessions.find((s) => s.id === sessionId);
      const emp = session ? employees.find((e) => e.id === session.employeeId) : undefined;
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? {
                ...s,
                riskState: 'VERY HIGH',
                status: 'Restricted',
                currentResponse: 'Loss of Privileges',
              }
            : s,
        ),
      );
      if (session) {
        setEmployees((prev) =>
          prev.map((employee) =>
            employee.id === session.employeeId
              ? { ...employee, accountStatus: 'Restricted', currentRisk: 'VERY HIGH' }
              : employee,
          ),
        );
      }
      addAudit({
        event: 'Privileges restricted',
        target: `${emp?.name ?? 'Unknown'} / ${sessionId}`,
        action: 'Loss of Privileges',
        result: 'Success',
        details: 'Session privileges removed pending investigation.',
      });
    },
    [sessions, employees, addAudit],
  );

  const terminateSession = useCallback(
    (sessionId: string) => {
      const session = sessions.find((s) => s.id === sessionId);
      const emp = session ? employees.find((e) => e.id === session.employeeId) : undefined;
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? {
                ...s,
                status: 'Terminated',
                duration: 'Terminated',
                lifecycle: 'destroyed',
                destroyedTime: nowTimestamp(),
                terminationReason: 'Terminated by security operator',
                currentResponse: 'None',
              }
            : s,
        ),
      );
      addAudit({
        event: 'Session terminated',
        target: `${emp?.name ?? 'Unknown'} / ${sessionId}`,
        action: 'Session terminated',
        result: 'Success',
        details: 'Authenticated session ended by administrator.',
      });
    },
    [sessions, employees, addAudit],
  );

  const activateShadow = useCallback(
    (sessionId: string, reason: string) => {
      const session = sessions.find((s) => s.id === sessionId);
      const emp = session ? employees.find((e) => e.id === session.employeeId) : undefined;
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? {
                ...s,
                riskState: 'CRITICAL',
                status: 'Frozen',
                currentResponse: 'Freeze Account + Shadow Environment',
                shadowEnvironment: {
                  active: true,
                  triggerTime: nowTimestamp(),
                  reason,
                  status: 'Deception Routing: Active',
                },
              }
            : s,
        ),
      );
      if (session) {
        setEmployees((prev) =>
          prev.map((employee) =>
            employee.id === session.employeeId
              ? { ...employee, accountStatus: 'Frozen', currentRisk: 'CRITICAL' }
              : employee,
          ),
        );
      }
      addAudit({
        event: 'Shadow Environment activated',
        target: `${emp?.name ?? 'Unknown'} / ${sessionId}`,
        action: 'Freeze Account + Shadow Environment',
        result: 'Success',
        details: reason,
      });
    },
    [sessions, employees, addAudit],
  );

  const generateReport = useCallback(
    (employeeId: string) => {
      const emp = employees.find((e) => e.id === employeeId);
      if (!emp) {
        throw new Error('Employee not found');
      }
      const employeeDevices = devices.filter(
        (device): device is Device & { risk: RiskLevel; riskScore: number } =>
          device.employeeId === employeeId &&
          device.status === 'Approved' &&
          device.risk !== undefined &&
          device.riskScore !== undefined,
      );
      const generatedAt = nowTimestamp();
      const generatedReports = employeeDevices.map((device, index): SecurityReport => {
        const session =
          sessions.find(
            (item) =>
              item.deviceId === device.id &&
              item.lifecycle === 'active' &&
              item.status !== 'Terminated',
          ) ?? sessions.find((item) => item.deviceId === device.id);
        return {
          id: `RPT-${Date.now().toString(36).toUpperCase()}-${index + 1}`,
          ...buildEmployeeSecurityReport(emp, device, session, generatedAt),
        };
      });

      if (generatedReports.length === 0) return generatedReports;

      setReports((prev) => [...generatedReports, ...prev]);
      addAudit({
        event: 'AI security report generated',
        target: emp.name,
        action: 'Generate AI Security Report',
        result: 'Success',
        details: `${generatedReports.length} device report(s) generated for continuous authentication review.`,
      });
      return generatedReports;
    },
    [employees, devices, sessions, addAudit],
  );

  const value = useMemo(
    () => ({
      employees,
      devices,
      sessions,
      alerts,
      auditEvents,
      securityEvents,
      behavioral,
      reports,
      addAudit,
      approveDevice,
      denyDevice,
      removeDevice,
      blockDevice,
      unfreezeAccount,
      triggerReauth,
      restrictSession,
      terminateSession,
      activateShadow,
      generateReport,
      getEmployee,
      getDevice,
      getSession,
      syncEmployeeCounts,
    }),
    [
      employees,
      devices,
      sessions,
      alerts,
      auditEvents,
      securityEvents,
      behavioral,
      reports,
      addAudit,
      approveDevice,
      denyDevice,
      removeDevice,
      blockDevice,
      unfreezeAccount,
      triggerReauth,
      restrictSession,
      terminateSession,
      activateShadow,
      generateReport,
      getEmployee,
      getDevice,
      getSession,
      syncEmployeeCounts,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
