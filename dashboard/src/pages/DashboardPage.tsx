import {
  Area,
  Bar,
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
import { useMemo } from 'react';
import { TopBar } from '../components/layout/TopBar';
import { useApp } from '../context/AppContext';
import { activityDetectionData } from '../data/mockData';
import { riskLevels, type RiskLevel } from '../types';

const riskColors: Record<RiskLevel, string> = {
  LOW: '#22c55e',
  MEDIUM: '#3b82f6',
  HIGH: '#f59e0b',
  'VERY HIGH': '#e11d48',
  CRITICAL: '#ef4444',
};

export function DashboardPage() {
  const { employees } = useApp();
  const riskSummary = useMemo(() => {
    return riskLevels.map((level) => ({
      name: level,
      value: employees.filter((employee) => employee.currentRisk === level).length,
      color: riskColors[level],
    }));
  }, [employees]);

  return (
    <>
      <TopBar title="Security Overview" />
      <div className="app-page">
        <div className="mx-auto max-w-[1440px] space-y-5">
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
                  Real-time behavioral monitoring across keyboard, mouse, and anomaly signals
                </p>
              </div>
              <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs font-medium text-slate-600">
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-teal-700" />
                  Keyboard activity
                </span>
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-orange-500" />
                  Mouse activity
                </span>
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-red-600" />
                  Anomalies
                </span>
                <span className="flex items-center gap-2">
                  <span className="w-4 border-t border-dashed border-slate-500" />
                  Baseline
                </span>
              </div>
            </div>
            <div className="px-3 pb-4 pt-5 sm:px-6 sm:pb-6">
              <div className="h-[300px] min-w-0 sm:h-[340px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={activityDetectionData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="keyboardGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#0f766e" stopOpacity={0.24} />
                        <stop offset="100%" stopColor="#0f766e" stopOpacity={0.025} />
                      </linearGradient>
                      <linearGradient id="mouseGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#f97316" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="#f97316" stopOpacity={0.025} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 5" stroke="#e9eef3" vertical={false} />
                    <XAxis dataKey="window" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} dy={8} />
                    <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} domain={[0, 4]} />
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
                      dataKey="keyboard"
                      name="Keyboard activity"
                      stroke="#0f766e"
                      fill="url(#keyboardGradient)"
                      strokeWidth={2.5}
                      activeDot={{ r: 5, strokeWidth: 0 }}
                    />
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="mouse"
                      name="Mouse activity"
                      stroke="#f97316"
                      fill="url(#mouseGradient)"
                      strokeWidth={2.5}
                      activeDot={{ r: 5, strokeWidth: 0 }}
                    />
                    <Bar
                      yAxisId="right"
                      dataKey="anomalies"
                      name="Anomalies"
                      fill="#dc2626"
                      radius={[4, 4, 0, 0]}
                      barSize={16}
                    />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="baseline"
                      name="Baseline"
                      stroke="#64748b"
                      strokeDasharray="4 4"
                      strokeWidth={1.5}
                      dot={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-right text-[11px] text-slate-400">Analysis window</p>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
