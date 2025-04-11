import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const startTask = async (task) => {
  try {
    const response = await api.post('/api/tasks/start', task);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.message || 'Failed to start task');
  }
};

export const stopTask = async (taskId) => {
  try {
    const response = await api.post(`/api/tasks/${taskId}/stop`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.message || 'Failed to stop task');
  }
};

export const getTaskStatus = async (taskId) => {
  try {
    const response = await api.get(`/api/tasks/${taskId}/status`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.message || 'Failed to get task status');
  }
};

export const getHistory = async () => {
  try {
    const response = await api.get('/api/history');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.message || 'Failed to get history');
  }
};

export const updateSettings = async (settings) => {
  try {
    const response = await api.put('/api/settings', settings);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.message || 'Failed to update settings');
  }
};

export const getSettings = async () => {
  try {
    const response = await api.get('/api/settings');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.message || 'Failed to get settings');
  }
};

export default api; 