import { ChevronDown, ChevronRight, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { TopBar } from '../components/layout/TopBar';
import { Badge, riskVariant } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useApp } from '../context/AppContext';
import { useDeviceActions } from '../hooks/useDeviceActions';
import { isSupportedChromiumBrowser } from '../utils/browserSupport';
import type { Device, Employee } from '../types';

function employeeMatchesQuery(emp: Employee, query: string) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return emp.name.toLowerCase().includes(q) || emp.id.toLowerCase().includes(q);
}

export function DevicesPage() {
  const { employees, devices } = useApp();
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const { confirm, modal } = useDeviceActions('general');

  const approved = devices.filter((d) => d.status === 'Approved').length;
  const pending = devices.filter((d) => d.status === 'Pending').length;
  const blocked = devices.filter((d) => d.status === 'Blocked').length;

  const grouped = useMemo(() => {
    return employees
      .filter((e) => !e.role.toLowerCase().includes('admin') && employeeMatchesQuery(e, search))
      .map((emp) => ({
        employee: emp,
        devices: devices.filter((d) => d.employeeId === emp.id),
      }));
  }, [employees, devices, search]);

  const toggle = (id: string) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <>
      <TopBar title="Devices" />
      <div className="app-page">
        <div className="grid gap-4 sm:grid-cols-4">
          {[
            { label: 'Total Devices', value: devices.length },
            { label: 'Approved', value: approved },
            { label: 'Pending', value: pending },
            { label: 'Blocked', value: blocked },
          ].map((c) => (
            <div key={c.label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-card">
              <div className="text-xs text-gray-500">{c.label}</div>
              <div className="text-2xl font-bold text-gray-900">{c.value}</div>
            </div>
          ))}
        </div>

        <div className="relative mt-6 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            placeholder="Search by employee name or ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
          />
        </div>

        <div className="mt-6 space-y-3">
          {grouped.map(({ employee, devices: empDevices }) => {
            const isOpen = expanded[employee.id] ?? false;
            const count = empDevices.length;
            return (
              <div key={employee.id} className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-card">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left hover:bg-gray-50/80"
                  onClick={() => toggle(employee.id)}
                >
                  <div className="flex items-center gap-3">
                    {isOpen ? (
                      <ChevronDown className="h-4 w-4 text-brand-600" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-gray-400" />
                    )}
                    <div>
                      <div className="font-semibold text-gray-900">{employee.name}</div>
                      <div className="text-xs text-gray-500">
                        {count} Device{count === 1 ? '' : 's'} · Risk:{' '}
                        <span className="font-medium">{employee.currentRisk}</span>
                      </div>
                    </div>
                  </div>
                  <Badge variant={riskVariant(employee.currentRisk)}>{employee.currentRisk}</Badge>
                </button>

                {isOpen && (
                  <div className="space-y-3 border-t border-gray-100 bg-gray-50/50 px-5 py-4">
                    {empDevices.length === 0 ? (
                      <p className="text-sm text-gray-500">No devices registered.</p>
                    ) : (
                      empDevices.map((d) => (
                        <DeviceCard
                          key={d.id}
                          device={d}
                          onAccept={() => confirm('accept', d.id, d.status === 'Pending' ? 'pending' : 'general')}
                          onDeny={() => confirm('deny', d.id, d.status === 'Pending' ? 'pending' : 'general')}
                          onRemove={() => confirm('remove', d.id)}
                        />
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {grouped.length === 0 && (
            <div className="rounded-xl border border-dashed border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
              No employees match your search.
            </div>
          )}
        </div>
      </div>
      {modal}
    </>
  );
}

function DeviceCard({
  device,
  onAccept,
  onDeny,
  onRemove,
}: {
  device: Device;
  onAccept: () => void;
  onDeny: () => void;
  onRemove: () => void;
}) {
  const approved = device.status === 'Approved';
  const details: [string, string][] = [
    ...(approved
      ? ([['Device ID', device.id], ['Chromium browser', device.browser]] as [string, string][])
      : ([['Chromium browser', device.browser]] as [string, string][])),
    ...(approved
      ? ([
          ['First registered', device.firstRegistered ?? '—'],
          ['Last seen', device.lastSeen ?? '—'],
          ['Session IP', device.sessionIp ?? '—'],
          ['Risk', device.risk ?? '—'],
        ] as [string, string][])
      : []),
  ];

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-mono text-sm font-semibold text-gray-900">
          {approved ? device.id : 'Unknown device'}
        </h3>
        <Badge variant={riskVariant(device.status)}>{device.status}</Badge>
      </div>
      <dl className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
        {details.map(([label, value]) => (
          <div key={String(label)}>
            <dt className="text-xs text-gray-500">{label}</dt>
            <dd className="font-medium text-gray-900">{value}</dd>
          </div>
        ))}
      </dl>
      {device.status === 'Pending' && (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            className="!text-xs"
            onClick={onAccept}
            disabled={!isSupportedChromiumBrowser(device.browser)}
          >
            Accept
          </Button>
          <Button variant="danger" className="!text-xs" onClick={onDeny}>
            Deny
          </Button>
          {!isSupportedChromiumBrowser(device.browser) && (
            <span className="text-xs text-red-700">Unsupported browser: Chromium-based browsers only.</span>
          )}
        </div>
      )}
      {approved && (
        <div className="mt-4">
          <Button variant="danger" className="!text-xs" onClick={onRemove}>
            Remove Device
          </Button>
        </div>
      )}
    </div>
  );
}
