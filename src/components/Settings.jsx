import React from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../store';

const SettingSection = ({ title, children }) => (
  <div className="space-y-4">
    <h3 className="text-lg font-semibold">{title}</h3>
    <div className="space-y-4">{children}</div>
  </div>
);

const SettingItem = ({ label, children }) => (
  <div className="flex items-center justify-between">
    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
      {label}
    </label>
    <div className="w-48">{children}</div>
  </div>
);

const Settings = () => {
  const { settings, updateSettings } = useStore();

  const handleChange = (key, value) => {
    updateSettings({ [key]: value });
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Settings</h1>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 space-y-8"
      >
        <SettingSection title="Language Model">
          <SettingItem label="Provider">
            <select
              value={settings.llmProvider}
              onChange={(e) => handleChange('llmProvider', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700"
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="local">Local</option>
            </select>
          </SettingItem>

          <SettingItem label="Model">
            <select
              value={settings.llmModel}
              onChange={(e) => handleChange('llmModel', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700"
            >
              <option value="gpt-4">GPT-4</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              <option value="claude-2">Claude 2</option>
            </select>
          </SettingItem>

          <SettingItem label="Temperature">
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.temperature}
              onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
              className="w-full"
            />
            <span className="text-xs text-gray-500">{settings.temperature}</span>
          </SettingItem>
        </SettingSection>

        <SettingSection title="Agent Configuration">
          <SettingItem label="Max Steps">
            <input
              type="number"
              value={settings.maxSteps}
              onChange={(e) => handleChange('maxSteps', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700"
            />
          </SettingItem>

          <SettingItem label="Use Vision">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.useVision}
                onChange={(e) => handleChange('useVision', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
            </label>
          </SettingItem>

          <SettingItem label="Headless Mode">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.headless}
                onChange={(e) => handleChange('headless', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
            </label>
          </SettingItem>
        </SettingSection>
      </motion.div>
    </div>
  );
};

export default Settings; 