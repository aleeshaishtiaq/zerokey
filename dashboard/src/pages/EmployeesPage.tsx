import { Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TopBar } from '../components/layout/TopBar';
import { Badge, riskVariant } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useApp } from '../context/AppContext';
import type { Employee } from '../types';

function matchesEmployee(emp: Employee, query: string) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return emp.name.toLowerCase().includes(q) || emp.id.toLowerCase().includes(q);
}

export function EmployeesPage() {
  const { employees } = useApp();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');

  const filtered = useMemo(
    () => employees.filter((e) => !e.role.toLowerCase().includes('admin') && matchesEmployee(e, search)),
    [employees, search],
  );

  return (
    <>
      <TopBar title="Employees" />
      <div className="app-page">
        <div className="relative mb-4 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            placeholder="Search by name or employee ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                <th className="px-4 py-3">Employee</th>
                <th className="px-4 py-3">Employee ID</th>
                <th className="px-4 py-3">Department</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Account Status</th>
                <th className="px-4 py-3">Devices</th>
                <th className="px-4 py-3">Current Risk</th>
                <th className="px-4 py-3">Last Active</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => (
                <tr key={e.id} className="border-b border-gray-50 hover:bg-gray-50/80">
                  <td className="px-4 py-3 font-medium text-gray-900">{e.name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{e.id}</td>
                  <td className="px-4 py-3">{e.department}</td>
                  <td className="px-4 py-3 text-gray-600">{e.role}</td>
                  <td className="px-4 py-3">
                    <Badge variant={e.accountStatus === 'Active' ? 'success' : 'danger'}>
                      {e.accountStatus}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">{e.registeredDevices}</td>
                  <td className="px-4 py-3">
                    <Badge variant={riskVariant(e.currentRisk)}>{e.currentRisk}</Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{e.lastActivity}</td>
                  <td className="px-4 py-3">
                    <Button variant="ghost" className="text-xs" onClick={() => navigate(`/employees/${e.id}`)}>
                      View
                    </Button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                    No employees match your search.
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
