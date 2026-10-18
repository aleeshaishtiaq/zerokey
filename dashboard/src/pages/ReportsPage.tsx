import { Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TopBar } from '../components/layout/TopBar';
import { Badge, riskVariant } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { useApp } from '../context/AppContext';
import type { Employee } from '../types';

function matchesEmployee(emp: Employee, query: string) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return emp.name.toLowerCase().includes(q) || emp.id.toLowerCase().includes(q);
}

export function ReportsPage() {
  const { employees, devices, generateReport } = useApp();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [confirmEmp, setConfirmEmp] = useState<Employee | null>(null);
  const [loading, setLoading] = useState(false);

  const filtered = useMemo(
    () => employees.filter((e) => !e.role.toLowerCase().includes('admin') && matchesEmployee(e, search)),
    [employees, search],
  );

  const onConfirmGenerate = () => {
    if (!confirmEmp) return;
    const employee = confirmEmp;
    setLoading(true);
    setTimeout(() => {
      const reports = generateReport(employee.id);
      setConfirmEmp(null);
      setLoading(false);
      navigate(`/reports/${employee.id}`, { state: { reports } });
    }, 500);
  };

  return (
    <>
      <TopBar title="Security Reports" />
      <div className="app-page">
        <div className="relative max-w-md">
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
          {filtered.map((emp) => {
            const deviceCount = devices.filter(
              (device) => device.employeeId === emp.id && device.status === 'Approved',
            ).length;
            return (
            <div
              key={emp.id}
              className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-gray-200 bg-white p-5 shadow-card"
            >
              <div>
                <div className="font-semibold text-gray-900">{emp.name}</div>
                <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <dt className="text-xs text-gray-500">Employee ID</dt>
                    <dd className="font-mono text-xs">{emp.id}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Department</dt>
                    <dd>{emp.department}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Current risk</dt>
                    <dd>
                      <Badge variant={riskVariant(emp.currentRisk)}>{emp.currentRisk}</Badge>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Last analysis</dt>
                    <dd className="text-gray-600">{emp.lastAnalysis}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Devices with reports</dt>
                    <dd>{deviceCount}</dd>
                  </div>
                </dl>
              </div>
              <Button onClick={() => setConfirmEmp(emp)} disabled={loading || deviceCount === 0}>
                Generate Device Reports
              </Button>
            </div>
            );
          })}
          {filtered.length === 0 && (
            <div className="rounded-xl border border-dashed border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
              No employees match your search.
            </div>
          )}
        </div>

      </div>

      <Modal
        open={!!confirmEmp}
        onClose={() => setConfirmEmp(null)}
        title="Generate Security Report?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmEmp(null)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={onConfirmGenerate} disabled={loading}>
              {loading ? 'Generating…' : 'Generate Device Reports'}
            </Button>
          </>
        }
      >
        {confirmEmp && (
          <p className="text-sm text-gray-700">
            A separate report will be generated for each of{' '}
            <strong>
              {devices.filter(
                (device) => device.employeeId === confirmEmp.id && device.status === 'Approved',
              ).length} approved device(s)
            </strong>{' '}
            assigned to <strong>{confirmEmp.name}</strong>, using available continuous
            authentication and behavioral analysis data.
          </p>
        )}
      </Modal>
    </>
  );
}
