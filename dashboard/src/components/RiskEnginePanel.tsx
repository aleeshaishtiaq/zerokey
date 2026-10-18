import type { RiskAction, Session } from '../types';
import { Badge, riskVariant } from './ui/Badge';

export function RiskEnginePanel({ session }: { session: Session }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-xs font-medium uppercase text-gray-500">Risk State</div>
          <div className="mt-2">
            <Badge variant={riskVariant(session.riskState)}>{session.riskState}</Badge>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ProtectionActionPanel({ action }: { action: RiskAction }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="text-sm font-semibold text-gray-900">Protection Action</div>
      <dl className="mt-3 space-y-2 text-sm">
        <div className="flex justify-between">
          <dt className="text-gray-500">Action</dt>
          <dd><Badge variant={riskVariant(action)}>{action}</Badge></dd>
        </div>
      </dl>
    </div>
  );
}
