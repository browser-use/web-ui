import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useStore } from './store';
import Sidebar from './components/Sidebar';
import TaskManager from './components/TaskManager';
import AgentDashboard from './components/AgentDashboard';
import Settings from './components/Settings';
import History from './components/History';

function App() {
  const { theme } = useStore();

  return (
    <Router>
      <div className={`min-h-screen ${theme === 'dark' ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          
          <main className="flex-1 overflow-y-auto p-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="max-w-7xl mx-auto"
            >
              <Routes>
                <Route path="/" element={<TaskManager />} />
                <Route path="/dashboard" element={<AgentDashboard />} />
                <Route path="/history" element={<History />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </motion.div>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App; 