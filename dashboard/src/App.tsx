import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { AppProvider } from './context/AppContext';
import { AccountManagementPage } from './pages/AccountManagementPage';
import { AlertsPage } from './pages/AlertsPage';
import { DashboardPage } from './pages/DashboardPage';
import { DevicesPage } from './pages/DevicesPage';
import { EmployeeReportPage } from './pages/EmployeeReportPage';
import { EmployeeDetailsPage } from './pages/EmployeeDetailsPage';
import { EmployeesPage } from './pages/EmployeesPage';
import { ReportsPage } from './pages/ReportsPage';
import { SessionInvestigationPage } from './pages/SessionInvestigationPage';
import { SessionsPage } from './pages/SessionsPage';
import { TelemetryPage } from './pages/TelemetryPage';
export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="employees" element={<EmployeesPage />} />
            <Route path="employees/:id" element={<EmployeeDetailsPage />} />
            <Route path="devices" element={<DevicesPage />} />
            <Route path="sessions" element={<SessionsPage />} />
            <Route path="telemetry" element={<TelemetryPage />} />
            <Route path="sessions/:id" element={<SessionInvestigationPage />} />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="reports/:employeeId" element={<EmployeeReportPage />} />
            <Route path="accounts" element={<AccountManagementPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}
