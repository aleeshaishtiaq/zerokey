import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { Sidebar } from './Sidebar';

export function AppLayout() {
  const { logout, user } = useAuth0();
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('zerokey-theme') === 'dark');

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('zerokey-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  return (
    <div className="app-shell flex h-screen overflow-hidden">
      <Sidebar darkMode={darkMode} onToggleDarkMode={() => setDarkMode((value) => !value)} />
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <div className="flex items-center justify-end gap-3 border-b border-gray-200 bg-white px-6 py-2 text-xs text-gray-600">
          <span>{user?.email ?? user?.sub}</span>
          <button
            type="button"
            onClick={() => void logout({ logoutParams: { returnTo: `${window.location.origin}/` } })}
            className="font-medium text-brand-700 hover:underline"
          >
            Sign out
          </button>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
