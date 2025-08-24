'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiService } from '@/services/api';

export interface NetworkStatus {
  isOnline: boolean;
  isConnected: boolean;
  latency: number | null;
  lastChecked: Date | null;
  error: string | null;
}

export interface NetworkActions {
  checkConnection: () => Promise<void>;
  startMonitoring: (interval?: number) => void;
  stopMonitoring: () => void;
}

const INITIAL_STATE: NetworkStatus = {
  isOnline: true,
  isConnected: true,
  latency: null,
  lastChecked: null,
  error: null,
};

export function useNetworkStatus(): [NetworkStatus, NetworkActions] {
  const [status, setStatus] = useState<NetworkStatus>(INITIAL_STATE);
  const monitoringIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isActiveRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    isActiveRef.current = true;
    return () => {
      isActiveRef.current = false;
      if (monitoringIntervalRef.current) {
        clearInterval(monitoringIntervalRef.current);
      }
    };
  }, []);

  const updateStatus = useCallback((updates: Partial<NetworkStatus>) => {
    if (!isActiveRef.current) return;
    setStatus(prev => ({ ...prev, ...updates }));
  }, []);

  // Monitor browser online/offline events
  useEffect(() => {
    const handleOnline = () => {
      updateStatus({ isOnline: true });
      // Check actual connectivity when coming back online
      checkConnection();
    };
    
    const handleOffline = () => {
      updateStatus({ 
        isOnline: false, 
        isConnected: false,
        error: 'Device is offline'
      });
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Set initial online status
    updateStatus({ isOnline: navigator.onLine });

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const checkConnection = useCallback(async () => {
    if (!isActiveRef.current) return;

    try {
      const result = await apiService.testConnection();
      
      updateStatus({
        isConnected: result.isConnected,
        latency: result.latency,
        lastChecked: new Date(),
        error: result.error || null,
      });
    } catch (error) {
      updateStatus({
        isConnected: false,
        latency: null,
        lastChecked: new Date(),
        error: error instanceof Error ? error.message : 'Connection test failed',
      });
    }
  }, [updateStatus]);

  const startMonitoring = useCallback((interval: number = 30000) => {
    if (monitoringIntervalRef.current) {
      clearInterval(monitoringIntervalRef.current);
    }

    // Initial check
    checkConnection();

    // Set up periodic checks
    monitoringIntervalRef.current = setInterval(() => {
      if (isActiveRef.current && status.isOnline) {
        checkConnection();
      }
    }, interval);
  }, [checkConnection, status.isOnline]);

  const stopMonitoring = useCallback(() => {
    if (monitoringIntervalRef.current) {
      clearInterval(monitoringIntervalRef.current);
      monitoringIntervalRef.current = null;
    }
  }, []);

  // Auto-start monitoring on mount
  useEffect(() => {
    startMonitoring();
    return stopMonitoring;
  }, [startMonitoring, stopMonitoring]);

  const actions: NetworkActions = {
    checkConnection,
    startMonitoring,
    stopMonitoring,
  };

  return [status, actions];
}