import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../store';
import { PlusIcon, PlayIcon, StopIcon } from '@heroicons/react/24/outline';

const TaskManager = () => {
  const { tasks, currentTask, agentStatus, addTask, setCurrentTask, setAgentStatus } = useStore();
  const [newTask, setNewTask] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (newTask.trim()) {
      const task = {
        id: Date.now(),
        text: newTask,
        status: 'pending',
        createdAt: new Date().toISOString(),
      };
      addTask(task);
      setNewTask('');
    }
  };

  const startTask = (task) => {
    setCurrentTask(task);
    setAgentStatus('running');
    // TODO: Connect to backend agent
  };

  const stopTask = () => {
    setAgentStatus('idle');
    // TODO: Stop backend agent
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Task Manager</h1>
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

      <motion.form 
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6"
      >
        <div className="flex space-x-4">
          <input
            type="text"
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
            placeholder="Enter a new task..."
            className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            <PlusIcon className="h-5 w-5" />
          </button>
        </div>
      </motion.form>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {tasks.map((task) => (
          <motion.div
            key={task.id}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">{task.text}</h3>
              <span className={`px-2 py-1 rounded-full text-xs ${
                task.status === 'completed' 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-yellow-100 text-yellow-800'
              }`}>
                {task.status}
              </span>
            </div>
            
            <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
              <span>Created: {new Date(task.createdAt).toLocaleString()}</span>
            </div>

            <div className="flex space-x-2">
              {currentTask?.id === task.id && agentStatus === 'running' ? (
                <button
                  onClick={stopTask}
                  className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center justify-center space-x-2"
                >
                  <StopIcon className="h-5 w-5" />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  onClick={() => startTask(task)}
                  className="flex-1 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors flex items-center justify-center space-x-2"
                >
                  <PlayIcon className="h-5 w-5" />
                  <span>Start</span>
                </button>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default TaskManager; 