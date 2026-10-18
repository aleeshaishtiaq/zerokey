import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { SecurityReportView } from '../components/SecurityReportView';
import { BreadcrumbItem, TopBar } from '../components/layout/TopBar';
import { Button } from '../components/ui/Button';
import { useApp } from '../context/AppContext';
import type { SecurityReport } from '../types';

export function EmployeeReportPage() {
  const { employeeId } = useParams<{ employeeId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { employees, reports } = useApp();
  const employee = employees.find((item) => item.id === employeeId);
  const locationState = location.state as { reports?: SecurityReport[] } | null;
  const employeeReports =
    locationState?.reports?.length
      ? locationState.reports
      : reports.filter((item) => item.employeeId === employeeId);

  return (
    <>
      <TopBar
        title={employee ? `${employee.name} Security Report` : 'Security Report'}
        breadcrumb={
          <>
            <BreadcrumbItem label="Security Reports" href="/reports" />
            {employee && <BreadcrumbItem label={employee.name} />}
          </>
        }
      />
      <div className="app-page">
        {employeeReports.length > 0 ? (
          <div className="space-y-8">
            <p className="text-sm text-gray-600">
              {employeeReports.length} device-specific report(s) for {employee?.name ?? employeeId}.
            </p>
            {employeeReports.map((report, index) => (
              <section key={report.id}>
                <div className="mb-3">
                  <h2 className="text-base font-semibold text-gray-900">
                    Device {index + 1}: {report.deviceId}
                  </h2>
                  <p className="text-xs text-gray-500">{report.deviceId}</p>
                </div>
                <SecurityReportView report={report} />
              </section>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
            <p className="text-sm text-gray-600">
              No report is available for this employee yet.
            </p>
            <Button className="mt-4" onClick={() => navigate('/reports')}>
              Back to Security Reports
            </Button>
          </div>
        )}
      </div>
    </>
  );
}