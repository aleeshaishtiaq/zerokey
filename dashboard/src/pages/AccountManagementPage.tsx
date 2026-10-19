import { useState } from 'react';
import { TopBar } from '../components/layout/TopBar';
import { Badge, riskVariant } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { useApp } from '../context/AppContext';
import type { Employee } from '../types';

export function AccountManagementPage() {
  const { employees, unfreezeAccount } = useApp();
  const [unfreezeTarget, setUnfreezeTarget] = useState<Employee | null>(null);

  const frozenAccounts = employees.filter((e) => e.accountStatus === 'Frozen');

  return (
    <>
      <TopBar title="Account Management" />
      <div className="app-page">
        <p className="mb-4 text-sm text-gray-600">
          Manage employee account access. Frozen accounts require explicit approval before access is restored.
        </p>
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                <th className="px-4 py-3">Employee</th>
                <th className="px-4 py-3">Employee ID</th>
                <th className="px-4 py-3">Department</th>
                <th className="px-4 py-3">Account Status</th>
                <th className="px-4 py-3">Current Risk</th>
                <th className="px-4 py-3">Last Activity</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {frozenAccounts.map((e) => (
                <tr key={e.id} className="border-b border-gray-50 hover:bg-gray-50/80">
                  <td className="px-4 py-3 font-medium text-gray-900">{e.name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{e.id}</td>
                  <td className="px-4 py-3">{e.department}</td>
                  <td className="px-4 py-3">
                    <Badge variant="danger">{e.accountStatus}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={riskVariant(e.currentRisk)}>{e.currentRisk}</Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{e.lastActivity}</td>
                  <td className="px-4 py-3">
                    <Button variant="primary" className="!text-xs" onClick={() => setUnfreezeTarget(e)}>
                      Unfreeze Account
                    </Button>
                  </td>
                </tr>
              ))}
              {frozenAccounts.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                    No frozen accounts at this time.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={!!unfreezeTarget}
        onClose={() => setUnfreezeTarget(null)}
        title="Unfreeze Account?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setUnfreezeTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                if (unfreezeTarget) unfreezeAccount(unfreezeTarget.id);
                setUnfreezeTarget(null);
              }}
            >
              Unfreeze Account
            </Button>
          </>
        }
      >
        {unfreezeTarget && (
          <p className="text-sm text-gray-700">
            Are you sure you want to restore access to <strong>{unfreezeTarget.name}</strong>&apos;s account?
          </p>
        )}
      </Modal>
    </>
  );
}
