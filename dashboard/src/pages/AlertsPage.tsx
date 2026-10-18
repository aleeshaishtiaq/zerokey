import { TopBar } from '../components/layout/TopBar';
import { useApp } from '../context/AppContext';

export function AlertsPage() {
  const { alerts, getEmployee } = useApp();
  const visibleAlerts = alerts.filter((alert) => alert.state !== 'Re-authentication Required');

  return (
    <>
      <TopBar title="Alerts" showSearch />
      <div className="app-page">
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Alert ID</th>
                <th className="px-4 py-3">Employee</th>
                <th className="px-4 py-3">Session</th>
                <th className="px-4 py-3">Trigger</th>
                <th className="px-4 py-3">Time</th>
              </tr>
            </thead>
            <tbody>
              {visibleAlerts.map((a) => {
                const emp = getEmployee(a.employeeId);
                return (
                  <tr key={a.id} className="border-b border-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">{a.id}</td>
                    <td className="px-4 py-3 font-medium">{emp?.name}</td>
                    <td className="px-4 py-3 font-mono text-xs">{a.sessionId}</td>
                    <td className="px-4 py-3 max-w-xs truncate text-gray-600" title={a.trigger}>
                      {a.trigger}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{a.timestamp}</td>
                  </tr>
                );
              })}
              {visibleAlerts.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No alerts to display.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
