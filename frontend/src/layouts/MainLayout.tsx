import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Activity, LayoutDashboard, History, User, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const MainLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navLinks = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/live-analysis', icon: Activity, label: 'Live Analysis' },
    { to: '/history', icon: History, label: 'History' },
    { to: '/profile', icon: User, label: 'Profile' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Navbar */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Activity className="h-8 w-8 text-blue-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">AthletiQ</span>
            </div>
            <div className="flex items-center space-x-4">
              {user && <span className="text-sm text-gray-600">{user.full_name}</span>}
              <button onClick={logout} className="p-2 text-gray-400 hover:text-red-500 transition-colors" title="Log out">
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 flex max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Sidebar */}
        <aside className="w-60 hidden sm:block pr-8 shrink-0">
          <nav className="space-y-1">
            {navLinks.map(({ to, icon: Icon, label }) => {
              const isActive = location.pathname === to;
              return (
                <Link
                  key={to}
                  to={to}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Icon className={`mr-3 h-5 w-5 ${isActive ? 'text-blue-500' : 'text-gray-400'}`} />
                  {label}
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
