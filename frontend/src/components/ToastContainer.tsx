'use client';

import { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import ToastComponent, { Toast, ToastType } from './Toast';

interface ToastContextType {
  showToast: (type: ToastType, title: string, message?: string, options?: Partial<Toast>) => void;
  showSuccess: (title: string, message?: string, options?: Partial<Toast>) => void;
  showError: (title: string, message?: string, options?: Partial<Toast>) => void;
  showWarning: (title: string, message?: string, options?: Partial<Toast>) => void;
  showInfo: (title: string, message?: string, options?: Partial<Toast>) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

interface ToastProviderProps {
  children: ReactNode;
}

export const ToastProvider = ({ children }: ToastProviderProps) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const showToast = useCallback((
    type: ToastType,
    title: string,
    message?: string,
    options?: Partial<Toast>
  ) => {
    const id = Math.random().toString(36).substr(2, 9);
    const toast: Toast = {
      id,
      type,
      title,
      message,
      duration: 5000, // Default 5 seconds
      ...options,
    };

    setToasts(prev => [...prev, toast]);

    // Auto-remove after duration if specified
    if (toast.duration && toast.duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, toast.duration);
    }
  }, [removeToast]);

  const showSuccess = useCallback((title: string, message?: string, options?: Partial<Toast>) => {
    showToast('success', title, message, options);
  }, [showToast]);

  const showError = useCallback((title: string, message?: string, options?: Partial<Toast>) => {
    showToast('error', title, message, { duration: 8000, ...options }); // Longer duration for errors
  }, [showToast]);

  const showWarning = useCallback((title: string, message?: string, options?: Partial<Toast>) => {
    showToast('warning', title, message, options);
  }, [showToast]);

  const showInfo = useCallback((title: string, message?: string, options?: Partial<Toast>) => {
    showToast('info', title, message, options);
  }, [showToast]);

  const contextValue: ToastContextType = {
    showToast,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    removeToast,
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      
      {/* Toast Container */}
      <div className="fixed top-4 right-4 z-50 space-y-2 w-96">
        {toasts.map(toast => (
          <ToastComponent
            key={toast.id}
            toast={toast}
            onClose={removeToast}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
};