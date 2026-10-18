import { useState } from 'react';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { useApp } from '../context/AppContext';

type Action = 'accept' | 'deny' | 'remove';
type DialogKind = 'pending' | 'general';

export function useDeviceActions(defaultKind: DialogKind = 'general') {
  const { approveDevice, denyDevice, removeDevice, getDevice } = useApp();
  const [pending, setPending] = useState<{ action: Action; deviceId: string; kind: DialogKind } | null>(
    null,
  );

  const device = pending ? getDevice(pending.deviceId) : undefined;
  const kind = pending?.kind ?? defaultKind;

  const titles: Record<Action, Record<DialogKind, string>> = {
    accept: {
      pending: 'Pending Device Connection',
      general: 'Accept Device?',
    },
    deny: {
      pending: 'Pending Device Connection',
      general: 'Deny Device?',
    },
    remove: {
      pending: 'Remove Device?',
      general: 'Remove Device?',
    },
  };

  const bodies: Record<Action, Record<DialogKind, string>> = {
    accept: {
      pending: 'Are you sure you want to accept this pending device connection?',
      general: 'Are you sure you want to accept this device?',
    },
    deny: {
      pending: 'Are you sure you want to deny this pending device connection?',
      general: 'Are you sure you want to deny this device?',
    },
    remove: {
      pending: 'Are you sure you want to remove this approved device?',
      general: 'Are you sure you want to remove this approved device?',
    },
  };

  const confirm = (action: Action, deviceId: string, kind: DialogKind = defaultKind) =>
    setPending({ action, deviceId, kind });

  const execute = () => {
    if (!pending) return;
    if (pending.action === 'accept') approveDevice(pending.deviceId);
    if (pending.action === 'deny') denyDevice(pending.deviceId);
    if (pending.action === 'remove') removeDevice(pending.deviceId);
    setPending(null);
  };

  const modal = (
    <Modal
      open={!!pending}
      onClose={() => setPending(null)}
      title={pending ? titles[pending.action][kind] : ''}
      footer={
        <>
          <Button variant="secondary" onClick={() => setPending(null)}>
            Cancel
          </Button>
          <Button
            variant={pending?.action === 'deny' || pending?.action === 'remove' ? 'danger' : 'primary'}
            onClick={execute}
          >
            {pending?.action === 'deny'
              ? 'Deny Device'
              : pending?.action === 'remove'
                ? 'Remove Device'
                : 'Accept Device'}
          </Button>
        </>
      }
    >
      {pending && <p className="text-sm text-gray-700">{bodies[pending.action][kind]}</p>}
      {device && (
        <p className="mt-3 text-sm text-gray-600">
          {device.status === 'Approved' && <strong>{device.id} · </strong>}
          {device.browser}
        </p>
      )}
    </Modal>
  );

  return { confirm, modal };
}
