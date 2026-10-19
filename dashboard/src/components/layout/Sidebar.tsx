import {
  AlertTriangle,
  FileText,
  LayoutDashboard,
  Laptop,
  Moon,
  Shield,
  Sun,
  UserCog,
  Users,
  Activity,
  Radio,
} from 'lucide-react';
import { NavLink } from 'react-router-dom';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/employees', label: 'Employees', icon: Users },
  { to: '/devices', label: 'Devices', icon: Laptop },
  { to: '/sessions', label: 'Sessions', icon: Activity },
  { to: '/telemetry', label: 'Telemetry', icon: Radio },
  { to: '/alerts', label: 'Alerts', icon: AlertTriangle },
  { to: '/reports', label: 'Security Reports', icon: FileText },
  { to: '/accounts', label: 'Account Management', icon: UserCog },
];

export function Sidebar({
  darkMode,
  onToggleDarkMode,
}: {
  darkMode: boolean;
  onToggleDarkMode: () => void;
}) {
  return (
    <aside className="flex h-full w-14 shrink-0 flex-col border-r border-brand-900 bg-brand-900 text-white sm:w-64">
      <div className="flex items-center justify-center gap-2.5 border-b border-white/10 px-2 py-4 sm:justify-start sm:px-5 sm:py-5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-500 text-white shadow-sm">
          <Shield className="h-5 w-5" />
        </div>
        <div className="hidden sm:block">
          <div className="text-sm font-bold tracking-tight text-white">ZeroKey</div>
          <div className="text-[10px] font-medium uppercase tracking-wider text-teal-200/70">Admin Console</div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-1.5 sm:p-3">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            aria-label={label}
            title={label}
            className={({ isActive }) =>
              `flex items-center justify-center gap-3 rounded-lg px-2 py-2.5 text-sm font-medium transition-colors sm:justify-start sm:px-3 ${
                isActive
                  ? 'bg-white/12 text-white shadow-inner'
                  : 'text-teal-100/70 hover:bg-white/8 hover:text-white'
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0 opacity-80" />
            <span className="hidden sm:inline">{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/10 p-1.5 sm:p-4">
        <button
          type="button"
          aria-pressed={darkMode}
          aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          onClick={onToggleDarkMode}
          className="mb-1 flex w-full items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/5 px-1 py-2 text-sm font-medium text-teal-50 hover:bg-white/10 sm:mb-3 sm:justify-between sm:px-3"
        >
          {darkMode ? <Sun className="h-4 w-4 shrink-0" /> : <Moon className="h-4 w-4 shrink-0" />}
          <span className="hidden items-center gap-2 sm:flex">
            {darkMode ? 'Light mode' : 'Dark mode'}
          </span>
          <span className="hidden text-xs text-teal-100/60 sm:inline">{darkMode ? 'On' : 'Off'}</span>
        </button>
      </div>
    </aside>
  );
}
