import { Link, useParams } from 'react-router-dom';
import { BehavioralPanel } from '../components/BehavioralPanel';
import { TopBar, BreadcrumbItem } from '../components/layout/TopBar';
import { ProtectionActionPanel, RiskEnginePanel } from '../components/RiskEnginePanel';
import { SessionActions } from '../components/SessionActions';
import { Badge, riskVariant } from '../components/ui/Badge';
import { useApp } from '../context/AppContext';
import { riskActionForLevel } from '../utils/riskAssessment';

export function SessionInvestigationPage() {
  const { id } = useParams<{ id: string }>();
  const { getSession, getEmployee, getDevice, behavioral, alerts } = useApp();
  const session = id ? getSession(id) : undefined;

  if (!session) {
    return (
      <>
        <TopBar title="Session not found" />
        <div className="p-6">
          <Link to="/sessions" className="text-brand-600">
            Back
          </Link>
        </div>
      </>
    );
  }

  const emp = getEmployee(session.employeeId);
  const dev = getDevice(session.deviceId);
  const behavior = behavioral[session.id];
  const ipChangeAlert = alerts.find(
    (alert) => alert.sessionId === session.id && alert.trigger.startsWith('IP changed during active session:'),
  );
  const newIp = ipChangeAlert?.trigger.split(' -> ').pop() ?? 'No IP change detected';

  return (
    <>
      <TopBar
        title={`Session Investigation — ${session.id}`}
        breadcrumb={
          <>
            <BreadcrumbItem label="Sessions" href="/sessions" />
            <BreadcrumbItem label={session.id} />
          </>
        }
      />
      <div className="app-page">
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
            <h2 className="text-sm font-semibold text-gray-900">Session Information</h2>
            <dl className="mt-4 space-y-2 text-sm">
              {[
                ['Session ID', session.id],
                ['Employee', emp?.name],
                ['Login time', session.loginTime],
                ['Device ID', dev?.status === 'Approved' ? dev.id : '—'],
                ['Session IP', dev?.status === 'Approved' ? session.sessionIp : '—'],
                ['New IP', newIp],
                ['Current status', session.status],
              ].map(([k, v]) => (
                <div key={String(k)} className="flex justify-between gap-4">
                  <dt className="text-gray-500">{k}</dt>
                  <dd
                    className={`font-medium ${k === 'New IP' && ipChangeAlert ? 'animate-pulse text-red-600' : 'text-gray-900'}`}
                  >
                    {v}
                  </dd>
                </div>
              ))}
            </dl>
          </section>
          <section className="space-y-4">
            <ProtectionActionPanel action={riskActionForLevel(session.riskState)} />
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-card">
              <h2 className="text-sm font-semibold">Response</h2>
              <p className="mt-2">
                <Badge variant={riskVariant(session.currentResponse)}>{session.currentResponse}</Badge>
              </p>
              {emp?.accountStatus === 'Frozen' && (
                <div className="mt-4">
                  <SessionActions session={session} />
                </div>
              )}
            </div>
          </section>
        </div>

        {dev?.status === 'Approved' && (
          <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-card">
            <h2 className="mb-4 text-sm font-semibold">AI Risk Engine</h2>
            <RiskEnginePanel session={session} />
          </section>
        )}

        {behavior && (
          <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-card">
            <h2 className="mb-4 text-sm font-semibold">Behavioral Analysis</h2>
            <BehavioralPanel data={behavior} />
          </section>
        )}

        {emp && (
          <div className="mt-6">
            <Link to={`/employees/${emp.id}`} className="text-sm font-medium text-brand-600 hover:underline">
              View employee security profile →
            </Link>
          </div>
        )}
      </div>
    </>
  );
}
