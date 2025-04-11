import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useStore = create(
  persist(
    (set) => ({
      theme: 'dark',
      tasks: [],
      currentTask: null,
      agentStatus: 'idle',
      settings: {
        llmProvider: 'openai',
        llmModel: 'gpt-4',
        temperature: 0.7,
        maxSteps: 10,
        useVision: true,
        headless: true,
      },
      history: [],
      
      // Actions
      setTheme: (theme) => set({ theme }),
      addTask: (task) => set((state) => ({ tasks: [...state.tasks, task] })),
      setCurrentTask: (task) => set({ currentTask: task }),
      setAgentStatus: (status) => set({ agentStatus: status }),
      updateSettings: (settings) => set((state) => ({ 
        settings: { ...state.settings, ...settings } 
      })),
      addToHistory: (entry) => set((state) => ({ 
        history: [...state.history, entry] 
      })),
      clearHistory: () => set({ history: [] }),
    }),
    {
      name: 'agent-storage',
    }
  )
);

export default useStore; 