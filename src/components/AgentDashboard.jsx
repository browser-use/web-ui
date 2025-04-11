import React from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../store';
import {
  ChartBarIcon,
  CursorArrowRaysIcon,
  ClockIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

const StatCard = ({ icon: Icon, title, value, color }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 ${color}`}
  >
    <div className="flex items-center">
      <div className="p-3 rounded-full bg-opacity-10 bg-white">
        <Icon className="h-6 w-6" />
      </div>
      <div className="ml-4">
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
        <p className="text-2xl font-semibold">{value}</p>
      </div>
    </div>
  </motion.div>
);

const ActivityLog = ({ activities }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6"
  >
    <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
    <div className="space-y-4">
      {activities.map((activity, index) => (
        <div key={index} className="flex items-start space-x-4">
          <div className="flex-shrink-0">
            <div className="w-2 h-2 rounded-full bg-primary-500 mt-2" />
          </div>
          <div>
            <p className="text-sm font-medium">{activity.action}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {new Date(activity.timestamp).toLocaleString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  </motion.div>
);

const AgentDashboard = () => {
  const { currentTask, agentStatus, history } = useStore();

  const stats = [
    {
      icon: CursorArrowRaysIcon,
      title: 'Actions Taken',
      value: history.length,
      color: 'bg-blue-50 dark:bg-blue-900/20',
    },
    {
      icon: ClockIcon,
      title: 'Active Time',
      value: '2h 30m',
      color: 'bg-green-50 dark:bg-green-900/20',
    },
    {
      icon: CheckCircleIcon,
      title: 'Success Rate',
      value: '95%',
      color: 'bg-purple-50 dark:bg-purple-900/20',
    },
  ];

  const recentActivities = history.slice(-5).reverse();

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Agent Dashboard</h1>
        <div className="flex items-center space-x-4">
          <span className={`px-3 py-1 rounded-full text-sm ${
            agentStatus === 'running' 
              ? 'bg-green-100 text-green-800' 
              : 'bg-gray-100 text-gray-800'
          }`}>
            {agentStatus}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat, index) => (
          <StatCard key={index} {...stat} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ActivityLog activities={recentActivities} />
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6"
        >
          <h3 className="text-lg font-semibold mb-4">Current Task</h3>
          {currentTask ? (
            <div className="space-y-4">
              <p className="text-gray-700 dark:text-gray-300">{currentTask.text}</p>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Started: {new Date(currentTask.createdAt).toLocaleString()}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400">No active task</p>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default AgentDashboard; 