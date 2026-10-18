import type { ReactNode } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Badge } from './ui/Badge';
import type { DeviationLevel, SecurityReport } from '../types';
import { useApp } from '../context/AppContext';

function deviationVariant(level: DeviationLevel) {
  if (level === 'Low') return 'success' as const;
  if (level === 'Mild') return 'warning' as const;
  if (level === 'Moderate') return 'warning' as const;
  return 'danger' as const;
}

function timelineStateColor(state: string) {
  if (state === 'Normal') return 'bg-emerald-500';
  if (state.includes('Mild')) return 'bg-amber-400';
  if (state.includes('Significant')) return 'bg-brand-600';
  return 'bg-gray-400';
}

export function SecurityReportView({ report }: { report: SecurityReport }) {
  const { getEmployee } = useApp();
  const emp = getEmployee(report.employeeId);

  return (
    <article className="rounded-xl border border-gray-200 bg-white p-8 shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-100 pb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Continuous Authentication Security Report</h2>
          <p className="mt-1 text-sm text-gray-500">
            {report.id} · Generated {report.generatedAt}
          </p>
        </div>
      </div>

      <section className="mt-6">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Employee Information</h3>
        <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          {[
            ['Employee name', emp?.name],
            ['Employee ID', report.employeeId],
            ['Device ID', report.deviceId],
            ['Department', report.department],
            ['Report generation time', report.generatedAt],
            ['Session ID', report.sessionId],
            ['Current session / status', report.currentSessionStatus],
          ].map(([label, value]) => (
            <div key={String(label)}>
              <dt className="text-gray-500">{label}</dt>
              <dd className="font-medium text-gray-900">{value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-8 rounded-lg border border-gray-200 bg-gray-50 p-5">
        <h3 className="text-sm font-semibold text-gray-900">Overall Risk Summary</h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryTile label="Risk state" value={report.riskState} />
          <SummaryTile label="Anomalous windows" value={String(report.anomalousWindowCount)} />
          <SummaryTile label="Consecutive anomalous" value={String(report.consecutiveAnomalousWindows)} />
          <SummaryTile label="Current response" value={report.currentResponse} />
        </div>
      </section>

      <section className="mt-8">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Behavioral Trend Over Time</h3>
        <p className="mt-1 text-xs text-gray-500">
          Continuous authentication windows — mild fluctuations may reflect natural human variation.
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
                <th className="py-2 pr-4">Time</th>
                <th className="py-2">Behavioral state</th>
              </tr>
            </thead>
            <tbody>
              {report.behavioralTimeline.map((row) => (
                <tr key={row.time} className="border-b border-gray-50">
                  <td className="py-2 pr-4 font-mono text-xs">{row.time}</td>
                  <td className="py-2">
                    <span className="inline-flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${timelineStateColor(row.state)}`} />
                      {row.state}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-8 grid gap-6 lg:grid-cols-2">
        <ChartCard title="Keyboard behavioral trend">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={report.keyboardTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="time" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="typingRate" name="Typing rate" stroke="#7c3aed" dot={false} />
              <Line type="monotone" dataKey="dwellTime" name="Dwell time" stroke="#ec4899" dot={false} />
              <Line type="monotone" dataKey="ppLatency" name="PP latency" stroke="#94a3b8" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Keyboard rhythm (extended)">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={report.keyboardTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="time" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="rpLatency" name="RP latency" stroke="#6d28d9" dot={false} />
              <Line type="monotone" dataKey="pauseRhythm" name="Pause/rhythm" stroke="#db2777" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Mouse behavioral trend">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={report.mouseTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="time" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="velocity" name="Velocity" stroke="#7c3aed" dot={false} />
              <Line type="monotone" dataKey="pathLength" name="Path length" stroke="#ec4899" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Mouse interaction pattern">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={report.mouseTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="time" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="directionChange" name="Direction changes" stroke="#6d28d9" dot={false} />
              <Line type="monotone" dataKey="straightness" name="Straightness" stroke="#94a3b8" dot={false} />
              <Line type="monotone" dataKey="clickInterval" name="Click interval" stroke="#db2777" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>

      <section className="mt-8">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
          Behavioral profile comparison
        </h3>
        <p className="mt-1 text-xs text-gray-500">Established profile vs. current session — derived features only.</p>
        <div className="mt-4 overflow-hidden rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Feature</th>
                <th className="px-4 py-3">Baseline</th>
                <th className="px-4 py-3">Current</th>
                <th className="px-4 py-3">Deviation</th>
              </tr>
            </thead>
            <tbody>
              {report.profileComparison.map((row) => (
                <tr key={row.feature} className="border-t border-gray-100">
                  <td className="px-4 py-3 font-medium">{row.feature}</td>
                  <td className="px-4 py-3">{row.baseline}</td>
                  <td className="px-4 py-3">{row.current}</td>
                  <td className="px-4 py-3">
                    <Badge variant={deviationVariant(row.deviation)}>{row.deviation}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-8">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
          Continuous authentication timeline
        </h3>
        <ol className="mt-4 space-y-3 border-l-2 border-brand-200 pl-4">
          {report.continuousTimeline.map((item) => (
            <li key={`${item.time}-${item.event}`} className="text-sm">
              <span className="font-mono text-xs font-semibold text-brand-700">{item.time}</span>
              <span className="text-gray-700"> — {item.event}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-8">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500">ZeroKey security events</h3>
        <ul className="mt-3 flex flex-wrap gap-2">
          {report.securityEvents.map((ev) => (
            <Badge key={ev} variant="brand">
              {ev}
            </Badge>
          ))}
        </ul>
      </section>

      <section className="mt-8 rounded-lg border border-gray-200 bg-gray-50 p-5">
        <h3 className="text-sm font-semibold text-gray-900">Overall assessment</h3>
        <p className="mt-2 text-sm leading-relaxed text-gray-700">{report.overallAssessment}</p>
      </section>
    </article>
  );
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-gray-900">{value}</div>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h4 className="mb-2 text-sm font-semibold text-gray-900">{title}</h4>
      {children}
    </div>
  );
}
