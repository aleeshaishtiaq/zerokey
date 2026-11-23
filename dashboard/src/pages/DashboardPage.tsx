import {
  Area,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { TopBar } from '../components/layout/TopBar';
import { TelemetryFeatureValues } from '../components/TelemetryFeatureValues';
import { useApp } from '../context/AppContext';
import { riskLevels, type RiskLevel } from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8765')
  .trim()
  .replace(/\/+$/, '');

interface RecentTelemetryRecord {
  device_id: string;
  session_id: string;
  timestamp: string;
  public_ip_address: string | null;
  mouse_features: Record<string, number | null>;
  keyboard_features: Record<string, number | null>;
}

const riskColors: Record<RiskLevel, string> = {
  LOW: '#22c55e',
  MEDIUM: '#3b82f6',
  HIGH: '#f59e0b',
  'VERY HIGH': '#e11d48',
  CRITICAL: '#ef4444',
};

export function DashboardPage() {
  const { employees } = useApp();
  const { getAccessTokenSilently } = useAuth0();
  const [recentTelemetry, setRecentTelemetry] = useState<RecentTelemetryRecord[]>([]);
  const [telemetryError, setTelemetryError] = useState('');
  const [loadingTelemetry, setLoadingTelemetry] = useState(true);
  const riskSummary = useMemo(() => {
    return riskLevels.map((level) => ({
      name: level,
      value: employees.filter((employee) => employee.currentRisk === level).length,
      color: riskColors[level],
    }));
  }, [employees]);
  const activityChartData = useMemo(
    () =>
      [...recentTelemetry].reverse().map((record) => ({
        window: new Date(record.timestamp).toLocaleTimeString(),
        typingRate: record.keyboard_features.typing_rate_keystrokes_per_minute,
        mouseVelocity: record.mouse_features.average_velocity_px_per_second,
      })),
    [recentTelemetry],
  );

  useEffect(() => {
    let active = true;

    const loadRecentTelemetry = async () => {
      try {
        const accessToken = await getAccessTokenSilently();
        const response = await fetch(`${API_BASE_URL}/api/telemetry/recent?limit=5`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (!response.ok) {
          throw new Error(`Telemetry API returned HTTP ${response.status}.`);
        }
        const records = (await response.json()) as RecentTelemetryRecord[];
        if (active) {
          setRecentTelemetry(records);
          setTelemetryError('');
        }
      } catch (error) {
        if (active) {
          setTelemetryError(
            error instanceof Error ? error.message : 'Unable to load telemetry records.',
          );
        }
      } finally {
        if (active) {
          setLoadingTelemetry(false);
        }
      }
    };

    void loadRecentTelemetry();
    const timer = window.setInterval(() => void loadRecentTelemetry(), 15_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [getAccessTokenSilently]);

  return (
    <>
      <TopBar title="Security Overview" />
      <div className="app-page">
        <div className="mx-auto max-w-[1440px] space-y-5">
          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 sm:px-6">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Recent Activity</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Latest behavioral windows received from the enterprise portal
                </p>
              </div>
              <Link to="/telemetry" className="text-sm font-semibold text-cyan-700 hover:text-cyan-800">
                View all telemetry
              </Link>
            </div>
            {telemetryError ? (
              <p role="alert" className="px-5 py-6 text-sm text-red-700 sm:px-6">
                {telemetryError}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase text-slate-500">
                      <th className="px-5 py-3 sm:px-6">Device ID (SHA-256)</th>
                      <th className="px-5 py-3">Session ID</th>
                      <th className="px-5 py-3">Timestamp</th>
                      <th className="px-5 py-3">Public IP (ipify)</th>
                      <th className="px-5 py-3">Mouse features</th>
                      <th className="px-5 py-3 sm:px-6">Keyboard features</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentTelemetry.map((record) => (
                      <tr
                        key={`${record.session_id}-${record.timestamp}`}
                        className="border-b border-slate-50 last:border-0"
                      >
                        <td className="max-w-56 break-all px-5 py-3 font-mono text-xs sm:px-6">{record.device_id}</td>
                        <td className="max-w-40 break-all px-5 py-3 font-mono text-xs">
                          {record.session_id}
                        </td>
                        <td className="whitespace-nowrap px-5 py-3">
                          {new Date(record.timestamp).toLocaleString()}
                        </td>
                        <td className="whitespace-nowrap px-5 py-3 font-mono text-xs sm:px-6">
                          {record.public_ip_address ?? 'Not available'}
                        </td>
                        <td className="min-w-64 px-5 py-3">
                          <TelemetryFeatureValues values={record.mouse_features} />
                        </td>
                        <td className="min-w-64 px-5 py-3">
                          <TelemetryFeatureValues values={record.keyboard_features} />
                        </td>
                      </tr>
                    ))}
                    {recentTelemetry.length === 0 && (
                      <tr>
                        <td colSpan={6} className="px-5 py-8 text-center text-slate-500 sm:px-6">
                          {loadingTelemetry
                            ? 'Loading activity…'
                            : 'No activity records have been received yet.'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 sm:px-6">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Risk Overview</h2>
                <p className="mt-1 text-sm text-slate-500">Current employee risk distribution</p>
              </div>
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                Stable
              </div>
            </div>

            <div className="grid items-center gap-4 p-4 sm:p-6 lg:grid-cols-[minmax(280px,0.95fr)_minmax(280px,1.05fr)] lg:gap-8">
              <div className="relative mx-auto h-[270px] w-full max-w-[340px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={riskSummary}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={70}
                      outerRadius={104}
                      paddingAngle={3}
                      stroke="none"
                    >
                      {riskSummary.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        borderRadius: '8px',
                        border: '1px solid #e2e8f0',
                        boxShadow: '0 8px 24px rgba(15, 23, 42, 0.10)',
                        fontSize: '12px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-4xl font-semibold text-slate-900">{employees.length}</span>
                  <span className="mt-1 text-xs font-medium uppercase text-slate-500">Total employees</span>
                </div>
              </div>

              <div className="w-full max-w-xl justify-self-center lg:justify-self-stretch">
                <div className="mb-3 grid grid-cols-[1fr_auto] px-1 text-[11px] font-semibold uppercase text-slate-400">
                  <span>Risk category</span>
                  <span>Employees</span>
                </div>
                <div className="divide-y divide-slate-100">
                  {riskSummary.map((item) => (
                    <div key={item.name} className="flex items-center justify-between gap-4 py-3.5">
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="h-3 w-3 shrink-0 rounded-sm" style={{ backgroundColor: item.color }} />
                        <span className="truncate text-sm font-medium text-slate-700">{item.name}</span>
                      </div>
                      <span className="min-w-8 text-right text-xl font-semibold tabular-nums" style={{ color: item.color }}>
                        {item.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-col gap-4 border-b border-slate-100 px-5 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Activity Detection</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Live typing-rate and mouse-velocity measurements from recent telemetry
                </p>
              </div>
              <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs font-medium text-slate-600">
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-teal-700" />
                  Typing rate (keys/min)
                </span>
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-orange-500" />
                  Mouse velocity (px/s)
                </span>
              </div>
            </div>
            <div className="px-3 pb-4 pt-5 sm:px-6 sm:pb-6">
              {activityChartData.length ? (
                <>
                  <div className="h-[300px] min-w-0 sm:h-[340px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={activityChartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="keyboardGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#0f766e" stopOpacity={0.24} />
                            <stop offset="100%" stopColor="#0f766e" stopOpacity={0.025} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 5" stroke="#e9eef3" vertical={false} />
                        <XAxis dataKey="window" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} dy={8} />
                        <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
                        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
                        <Tooltip
                          contentStyle={{
                            borderRadius: '8px',
                            border: '1px solid #e2e8f0',
                            boxShadow: '0 8px 24px rgba(15, 23, 42, 0.10)',
                            fontSize: '12px',
                          }}
                        />
                        <Area
                          yAxisId="left"
                          type="monotone"
                          dataKey="typingRate"
                          name="Typing rate (keys/min)"
                          stroke="#0f766e"
                          fill="url(#keyboardGradient)"
                          strokeWidth={2.5}
                          activeDot={{ r: 5, strokeWidth: 0 }}
                        />
                        <Line
                          yAxisId="right"
                          type="monotone"
                          dataKey="mouseVelocity"
                          name="Mouse velocity (px/s)"
                          stroke="#f97316"
                          strokeWidth={2.5}
                          activeDot={{ r: 5, strokeWidth: 0 }}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="mt-2 text-right text-[11px] text-slate-400">
                    Latest telemetry windows, oldest to newest
                  </p>
                </>
              ) : (
                <p className="py-16 text-center text-sm text-slate-500">
                  {loadingTelemetry ? 'Loading behavioral telemetry…' : 'No behavioral telemetry available yet.'}
                </p>
              )}
            </div>
          </section>

        </div>
      </div>
    </>
  );
}
