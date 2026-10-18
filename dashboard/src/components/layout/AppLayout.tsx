import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

export function AppLayout() {
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('zerokey-theme') === 'dark');

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('zerokey-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  return (
    <div className="app-shell flex h-screen overflow-hidden">
      <Sidebar darkMode={darkMode} onToggleDarkMode={() => setDarkMode((value) => !value)} />
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
