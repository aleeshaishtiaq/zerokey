import { useState } from 'react';
import { useApp } from '../context/AppContext';
import type { Session } from '../types';
import { Button } from './ui/Button';
import { Modal } from './ui/Modal';

export function SessionActions({ session }: { session: Session }) {
  const { unfreezeAccount } = useApp();
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setConfirmOpen(true)}>Unfreeze Account</Button>
      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Unfreeze Account?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                unfreezeAccount(session.employeeId);
                setConfirmOpen(false);
              }}
            >
              Unfreeze Account
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-700">Restore account access for this session&apos;s employee?</p>
      </Modal>
    </>
  );
}
