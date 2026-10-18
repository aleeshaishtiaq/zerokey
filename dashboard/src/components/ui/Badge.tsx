import type { ReactNode } from 'react';

const variants: Record<string, string> = {
  default: 'bg-gray-100 text-gray-700 border-gray-200',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-50 text-amber-800 border-amber-200',
  danger: 'bg-red-50 text-red-700 border-red-200',
  brand: 'bg-brand-50 text-brand-700 border-brand-200',
  accent: 'bg-accent-50 text-accent-600 border-pink-200',
  purple: 'bg-brand-100 text-brand-800 border-brand-200',
  info: 'bg-blue-50 text-blue-700 border-blue-200',
};

export function riskVariant(risk: string): keyof typeof variants {
  if (risk === 'CRITICAL') return 'danger';
  if (risk === 'VERY HIGH') return 'accent';
  if (risk === 'HIGH' || risk === 'Step-up Re-authentication') return 'warning';
  if (risk === 'MEDIUM' || risk === 'Monitor') return 'info';
  if (risk === 'LOW' || risk === 'Acceptable') return 'success';
  if (risk.includes('Frozen') || risk.includes('Blocked')) return 'danger';
  if (risk.includes('Re-auth') || risk.includes('Suspicious')) return 'warning';
  if (risk.includes('Restricted')) return 'accent';
  if (risk === 'Denied') return 'danger';
  if (risk === 'Approved' || risk === 'Active' || risk === 'Resolved') return 'success';
  if (risk === 'Pending' || risk === 'Open' || risk === 'Investigating') return 'warning';
  return 'default';
}

export function Badge({
  children,
  variant = 'default',
  className = '',
}: {
  children: ReactNode;
  variant?: keyof typeof variants;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
