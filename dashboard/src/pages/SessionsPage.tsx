import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TopBar } from '../components/layout/TopBar';
import { Badge, riskVariant } from '../components/ui/Badge';
import { useApp } from '../context/AppContext';
import { riskLevels, type RiskLevel, type Session } from '../types';

type RiskFilter = 'all' | RiskLevel | 'suspicious';

const riskFilterClasses: Record<RiskLevel, string> = {
  LOW: 'border-emerald-700 bg-emerald-700 text-white',
  MEDIUM: 'border-blue-700 bg-blue-700 text-white',
  HIGH: 'border-orange-600 bg-orange-600 text-white',
  'VERY HIGH': 'border-rose-700 bg-rose-700 text-white',
  CRITICAL: 'border-red-800 bg-red-800 text-white',
};

const filters: { id: RiskFilter; label: string; activeClass: string }[] = [
  { id: 'all', label: 'All Sessions', activeClass: 'border-gray-800 bg-gray-800 text-white' },
  ...riskLevels.map((level) => ({ id: level, label: level, activeClass: riskFilterClasses[level] })),
  { id: 'suspicious', label: 'Suspicious', activeClass: 'border-rose-700 bg-rose-700 text-white' },
];

export function SessionsPage() {
  const { sessions, getEmployee, getDevice } = useApp();
  const [filter, setFilter] = useState<RiskFilter>('all');
  const navigate = useNavigate();
  const visibleSessions = sessions.filter((session) => session.id !== 'S-1092');

  const filtered = useMemo(
    () => visibleSessions.filter((session) => {
      if (filter === 'all') return true;
      if (filter === 'suspicious') return session.status === 'Suspicious';
      return session.riskState === filter;
    }),
    [visibleSessions, filter],
  );

  return (
    <>
      <TopBar title="Sessions" showSearch />
      <div className="app-page">
        <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter sessions by risk">
          {filters.map((item) => {
            const count = visibleSessions.filter((session) => {
              if (item.id === 'all') return true;
              if (item.id === 'suspicious') return session.status === 'Suspicious';
              return session.riskState === item.id;
            }).length;
            const selected = filter === item.id;
            return (
              <button
                key={item.id}
                type="button"
                aria-pressed={selected}
                className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                  selected
                    ? item.activeClass
                    : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
                }`}
                onClick={() => setFilter(item.id)}
              >
                {item.label}
                <span className={`rounded px-1.5 py-0.5 text-xs ${selected ? 'bg-white/20' : 'bg-gray-100 text-gray-600'}`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-card">
          <SessionTable
            rows={filtered}
            onRowClick={(id) => navigate(`/sessions/${id}`)}
            getEmployee={getEmployee}
            getDevice={getDevice}
          />
        </div>
      </div>
    </>
  );
}

function SessionTable({
  rows,
  onRowClick,
  getEmployee,
  getDevice,
}: {
  rows: Session[];
  onRowClick: (id: string) => void;
  getEmployee: (id: string) => import('../types').Employee | undefined;
  getDevice: (id: string) => import('../types').Device | undefined;
}) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs uppercase text-gray-500">
          <th className="px-4 py-3">Session ID</th>
          <th className="px-4 py-3">Employee</th>
          <th className="px-4 py-3">Device</th>
          <th className="px-4 py-3">Session IP</th>
          <th className="px-4 py-3">Lifecycle</th>
          <th className="px-4 py-3">Login Time</th>
          <th className="px-4 py-3">Risk State</th>
          <th className="px-4 py-3">Status</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((s) => {
          const emp = getEmployee(s.employeeId);
          const dev = getDevice(s.deviceId);
          return (
            <tr
              key={s.id}
              className="cursor-pointer border-b border-gray-50 hover:bg-brand-50/40"
              onClick={() => onRowClick(s.id)}
            >
              <td className="px-4 py-3 font-mono text-xs">{s.id}</td>
              <td className="px-4 py-3 font-medium">{emp?.name}</td>
              <td className="px-4 py-3 font-mono text-xs">
                {dev?.status === 'Approved' ? dev.id : '—'}
              </td>
              <td className="px-4 py-3 font-mono text-xs">
                {dev?.status === 'Approved' ? s.sessionIp : '—'}
              </td>
              <td className="px-4 py-3 capitalize">{s.lifecycle.replace('_', ' ')}</td>
              <td className="px-4 py-3">{s.loginTime}</td>
              <td className="px-4 py-3">
                <Badge variant={riskVariant(s.riskState)}>{s.riskState}</Badge>
              </td>
              <td className="px-4 py-3">
                <Badge variant={riskVariant(s.status)}>
                  {s.status === 'Re-authentication Required' ? 'Active' : s.status}
                </Badge>
              </td>
            </tr>
          );
        })}
        {rows.length === 0 && (
          <tr>
            <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
              No sessions in this category.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
