import { Bell, ChevronRight, Search, ShieldCheck } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

export function TopBar({
  title,
  breadcrumb,
  showSearch = false,
}: {
  title: string;
  breadcrumb?: ReactNode;
  showSearch?: boolean;
}) {
  return (
    <header className="z-10 flex h-[68px] shrink-0 items-center justify-between border-b border-gray-200/80 bg-white/95 px-4 shadow-[0_1px_4px_rgba(15,35,39,0.04)] backdrop-blur sm:px-6">
      <div>
        {breadcrumb && (
          <div className="mb-0.5 flex items-center gap-1 text-xs text-gray-400">{breadcrumb}</div>
        )}
        <h1 className="text-lg font-semibold tracking-tight text-gray-900">{title}</h1>
      </div>
      <div className="flex items-center gap-4">
        <div className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 md:flex">
          <ShieldCheck className="h-3.5 w-3.5" />
          Monitoring Active
        </div>
        {showSearch && (
          <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="search"
              placeholder="Search..."
              className="w-56 rounded-lg border border-gray-200 bg-gray-50 py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </div>
        )}
        <button type="button" className="relative rounded-lg p-2 text-gray-500 hover:bg-gray-100">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-accent-500" />
        </button>
        <div className="flex h-9 w-9 items-center justify-center rounded-full border border-brand-100 bg-brand-50 text-brand-700" aria-label="Security console">
          <ShieldCheck className="h-4 w-4" />
        </div>
      </div>
    </header>
  );
}

export function BreadcrumbItem({ label, href }: { label: string; href?: string }) {
  if (href) {
    return (
      <>
        <Link to={href} className="hover:text-brand-600">
          {label}
        </Link>
        <ChevronRight className="h-3 w-3" />
      </>
    );
  }
  return <span className="text-gray-600">{label}</span>;
}
