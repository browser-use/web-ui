import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useStore } from '../store';
import {
  HomeIcon,
  ChartBarIcon,
  ClockIcon,
  Cog6ToothIcon,
  SunIcon,
  MoonIcon,
} from '@heroicons/react/24/outline';

const Sidebar = () => {
  const { theme, setTheme } = useStore();
  const location = useLocation();

  const navItems = [
    { path: '/', icon: HomeIcon, label: 'Tasks' },
    { path: '/dashboard', icon: ChartBarIcon, label: 'Dashboard' },
    { path: '/history', icon: ClockIcon, label: 'History' },
    { path: '/settings', icon: Cog6ToothIcon, label: 'Settings' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="w-64 bg-white dark:bg-gray-800 shadow-lg h-screen fixed left-0 top-0"
    >
      <div className="p-6">
        <h1 className="text-2xl font-bold text-primary-500">King Tadj</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">AI Web Browser Agent</p>
      </div>

      <nav className="mt-8">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center px-6 py-3 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-600 dark:bg-gray-700 dark:text-primary-400'
                  : 'text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
              <item.icon className="h-5 w-5 mr-3" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="absolute bottom-0 left-0 right-0 p-6">
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="flex items-center justify-center w-full px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 dark:text-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 transition-colors"
        >
          {theme === 'dark' ? (
            <>
              <SunIcon className="h-5 w-5 mr-2" />
              Light Mode
            </>
          ) : (
            <>
              <MoonIcon className="h-5 w-5 mr-2" />
              Dark Mode
            </>
          )}
        </button>
      </div>
    </motion.div>
  );
};

export default Sidebar; 