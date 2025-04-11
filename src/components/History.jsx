import React from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../store';
import { ClockIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

const HistoryItem = ({ item }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-500" />;
      default:
        return <ClockIcon className="h-5 w-5 text-yellow-500" />;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 space-y-4"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {getStatusIcon(item.status)}
          <h3 className="text-lg font-semibold">{item.task}</h3>
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {new Date(item.timestamp).toLocaleString()}
        </span>
      </div>

      <div className="space-y-2">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium">Duration:</span>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {item.duration}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium">Steps:</span>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {item.steps}
          </span>
        </div>
      </div>

      {item.result && (
        <div className="mt-4">
          <h4 className="text-sm font-medium mb-2">Result</h4>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {item.result}
          </p>
        </div>
      )}

      {item.error && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-red-500 mb-2">Error</h4>
          <p className="text-sm text-red-500">{item.error}</p>
        </div>
      )}
    </motion.div>
  );
};

const History = () => {
  const { history, clearHistory } = useStore();

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">History</h1>
        {history.length > 0 && (
          <button
            onClick={clearHistory}
            className="px-4 py-2 text-sm font-medium text-red-500 hover:text-red-600 transition-colors"
          >
            Clear History
          </button>
        )}
      </div>

      {history.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-12"
        >
          <ClockIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            No history yet
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Your agent's activities will appear here
          </p>
        </motion.div>
      ) : (
        <div className="space-y-4">
          {history.map((item, index) => (
            <HistoryItem key={index} item={item} />
          ))}
        </div>
      )}
    </div>
  );
};

export default History; 