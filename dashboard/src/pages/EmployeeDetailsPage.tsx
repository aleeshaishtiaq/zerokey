import { Link, useParams } from 'react-router-dom';
import { BehavioralPanel } from '../components/BehavioralPanel';
import { TopBar, BreadcrumbItem } from '../components/layout/TopBar';
import { Badge, riskVariant } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { useApp } from '../context/AppContext';
import { useState } from 'react';

export function EmployeeDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const {
    getEmployee,
    devices,
    sessions,
    behavioral,
    unfreezeAccount,
  } = useApp();
  const emp = id ? getEmployee(id) : undefined;
  const [unfreezeOpen, setUnfreezeOpen] = useState(false);

  if (!emp) {
    return (
      <>
        <TopBar title="Employee not found" />
        <div className="p-6">
          <Link to="/employees" className="text-brand-600">
            Back to employees
          </Link>
        </div>
      </>
    );
  }

  const empDevices = devices.filter((d) => d.employeeId === emp.id);
  const empSessions = sessions.filter((s) => s.employeeId === emp.id);
  const primarySession = empSessions.find((s) => s.status !== 'Terminated') ?? empSessions[0];
  const behavior = primarySession ? behavioral[primarySession.id] : undefined;
  const currentDevice = primarySession
    ? empDevices.find((d) => d.id === primarySession.deviceId)
    : empDevices[0];
  const enrolledDevice = empDevices.find((device) => device.id === emp.enrolledDeviceId);
  const deviceMatch = emp.enrolledDeviceId && enrolledDevice?.status === 'Approved' && currentDevice
    ? emp.enrolledDeviceId === currentDevice.id ? 'Same' : 'Different'
    : '—';

  return (
    <>
      <TopBar
        title={emp.name}
        breadcrumb={
          <>
            <BreadcrumbItem label="Employees" href="/employees" />
            <BreadcrumbItem label={emp.name} />
          </>
        }
      />
      <div className="app-page">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm text-gray-500">{emp.id}</span>
              <Badge variant={emp.accountStatus === 'Active' ? 'success' : 'danger'}>
                {emp.accountStatus}
              </Badge>
              <Badge variant={riskVariant(emp.currentRisk)}>{emp.currentRisk}</Badge>
            </div>
            <p className="mt-1 text-sm text-gray-600">
              {emp.department} · {emp.role}
            </p>
          </div>
          {emp.accountStatus === 'Frozen' && (
            <Button variant="primary" onClick={() => setUnfreezeOpen(true)}>
              Unfreeze Account
            </Button>
          )}
        </div>

        <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h2 className="text-sm font-semibold text-gray-900">Security Overview</h2>
          <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ['Risk State', emp.currentRisk],
              ['Account Status', emp.accountStatus],
              ['Enrollment Status', emp.enrollmentStatus],
              ['Approved Devices', empDevices.filter((device) => device.status === 'Approved').length],
              ['Active Sessions', empSessions.filter((s) => s.status !== 'Terminated').length],
              ['Last Authentication', emp.lastAuthentication],
              ['Last Activity', emp.lastActivity],
              ['Session Status', primarySession?.status ?? 'No active session'],
            ].map(([k, v]) => (
              <div key={String(k)}>
                <dt className="text-xs text-gray-500">{k}</dt>
                <dd className="mt-0.5 text-sm font-medium text-gray-900">{v}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="mt-6 rounded-xl border border-gray-200 bg-white shadow-card">
          <div className="border-b border-gray-100 px-5 py-4">
            <h2 className="text-sm font-semibold">Devices</h2>
            <p className="text-xs text-gray-500">Registered Devices: {empDevices.length}</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                  <th className="px-4 py-2">Device ID</th>
                  <th className="px-4 py-2">Chromium browser</th>
                  <th className="px-4 py-2">First Registered</th>
                  <th className="px-4 py-2">Last Seen</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Verification</th>
                  <th className="px-4 py-2">Current Session</th>
                  <th className="px-4 py-2">Session IP</th>
                </tr>
              </thead>
              <tbody>
                {empDevices.map((d) => (
                  <tr key={d.id} className="border-b border-gray-50">
                    <td className="px-4 py-2 font-mono text-xs">{d.status === 'Approved' ? d.id : '—'}</td>
                    <td className="px-4 py-2">{d.status === 'Approved' ? d.browser : '—'}</td>
                    <td className="px-4 py-2 text-gray-500">{d.status === 'Approved' ? d.firstRegistered : '—'}</td>
                    <td className="px-4 py-2 text-gray-500">{d.status === 'Approved' ? d.lastSeen : '—'}</td>
                    <td className="px-4 py-2">
                      <Badge variant={riskVariant(d.status)}>{d.status}</Badge>
                    </td>
                    <td className="px-4 py-2 text-xs">{d.verificationStatus}</td>
                    <td className="px-4 py-2 font-mono text-xs">{d.status === 'Approved' ? d.currentSession ?? '—' : '—'}</td>
                    <td className="px-4 py-2 font-mono text-xs">{d.status === 'Approved' ? d.sessionIp ?? '—' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-6 rounded-xl border border-gray-200 bg-white shadow-card">
          <div className="border-b border-gray-100 px-5 py-4">
            <h2 className="text-sm font-semibold">Sessions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                  <th className="px-4 py-2">Session ID</th>
                  <th className="px-4 py-2">Login</th>
                  <th className="px-4 py-2">Device</th>
                  <th className="px-4 py-2">Session IP</th>
                  <th className="px-4 py-2">Risk State</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Response</th>
                </tr>
              </thead>
              <tbody>
                {empSessions.map((s) => {
                  const dev = empDevices.find((d) => d.id === s.deviceId);
                  return (
                  <tr key={s.id} className="border-b border-gray-50">
                    <td className="px-4 py-2">
                      <Link to={`/sessions/${s.id}`} className="font-mono text-xs text-brand-600 hover:underline">
                        {s.id}
                      </Link>
                    </td>
                    <td className="px-4 py-2">{s.loginTime}</td>
                    <td className="px-4 py-2 font-mono text-xs">{dev?.status === 'Approved' ? dev.id : '—'}</td>
                    <td className="px-4 py-2 font-mono text-xs">{dev?.status === 'Approved' ? s.sessionIp : '—'}</td>
                    <td className="px-4 py-2">
                      <Badge variant={riskVariant(s.riskState)}>{s.riskState}</Badge>
                    </td>
                    <td className="px-4 py-2">{s.status}</td>
                    <td className="px-4 py-2 text-xs">{s.currentResponse}</td>
                  </tr>
                );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {behavior && (
          <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-card">
            <h2 className="mb-4 text-sm font-semibold text-gray-900">Behavioral Analysis</h2>
            <BehavioralPanel data={behavior} />
          </section>
        )}

        <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-card">
          <h2 className="text-sm font-semibold text-gray-900">Device Consistency</h2>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-gray-500">Enrolled Device</dt>
              <dd className="font-mono text-xs font-medium">
                {enrolledDevice?.status === 'Approved' ? enrolledDevice.id : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Current Device</dt>
              <dd className="font-mono text-xs font-medium">
                {currentDevice?.status === 'Approved' ? currentDevice.id : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Device Consistency</dt>
              <dd>
                <Badge variant={deviceMatch === 'Same' ? 'success' : deviceMatch === 'Different' ? 'warning' : 'default'}>
                  {deviceMatch}
                </Badge>
              </dd>
            </div>
          </dl>
          {deviceMatch === 'Different' && (
            <p className="mt-3 text-xs text-gray-500">
              A different device is a contextual risk signal only and does not automatically indicate an
              attacker.
            </p>
          )}
        </section>
      </div>

      <Modal
        open={unfreezeOpen}
        onClose={() => setUnfreezeOpen(false)}
        title="Unfreeze Account?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setUnfreezeOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                unfreezeAccount(emp.id);
                setUnfreezeOpen(false);
              }}
            >
              Unfreeze Account
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-700">
          Are you sure you want to restore access to {emp.name}&apos;s account?
        </p>
      </Modal>
    </>
  );
}
