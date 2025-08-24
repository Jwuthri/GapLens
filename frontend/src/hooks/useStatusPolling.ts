'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Analysis, AnalysisStatus } from '@/types';
import { apiService, ApiError } from '@/services/api';

export interface PollingConfig {
  interval: number;
  maxRetries: number;
  backoffMultiplier: number;
  maxInterval: number;
  enabled: boolean;
}

export interface PollingState {
  isPolling: boolean;
  error: string | null;
  retryCount: number;
  lastUpdated: Date | null;
  nextPollIn: number;
}

const DEFAULT_CONFIG: PollingConfig = {
  interval: 2000,
  maxRetries: 5,
  backoffMultiplier: 1.5,
  maxInterval: 10000,
  enabled: true,
};

export function useStatusPolling(
  analysisId: string | null,
  onStatusUpdate: (analysis: Analysis) => void,
  config: Partial<PollingConfig> = {}
) {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };
  const [state, setState] = useState<PollingState>({
    isPolling: false,
    error: null,
    retryCount: 0,
    lastUpdated: null,
    nextPollIn: 0,
  });

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const countdownRef = useRef<NodeJS.Timeout | null>(null);
  const currentIntervalRef = useRef(finalConfig.interval);
  const isActiveRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    isActiveRef.current = true;
    return () => {
      isActiveRef.current = false;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, []);

  const updateState = useCallback((updates: Partial<PollingState>) => {
    if (!isActiveRef.current) return;
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  const startCountdown = useCallback((duration: number) => {
    if (countdownRef.current) clearInterval(countdownRef.current);
    
    let remaining = duration;
    updateState({ nextPollIn: remaining });
    
    countdownRef.current = setInterval(() => {
      remaining -= 100;
      if (remaining <= 0) {
        if (countdownRef.current) clearInterval(countdownRef.current);
        updateState({ nextPollIn: 0 });
      } else {
        updateState({ nextPollIn: remaining });
      }
    }, 100);
  }, [updateState]);

  const calculateNextInterval = useCallback((retryCount: number): number => {
    const baseInterval = finalConfig.interval;
    const backoffInterval = baseInterval * Math.pow(finalConfig.backoffMultiplier, retryCount);
    return Math.min(backoffInterval, finalConfig.maxInterval);
  }, [finalConfig]);

  const pollStatus = useCallback(async (): Promise<void> => {
    if (!analysisId || !finalConfig.enabled || !isActiveRef.current) return;

    try {
      const analysis = await apiService.pollAnalysisStatus(
        analysisId,
        (progress, message) => {
          // Progress updates can be handled by parent component
        },
        (status) => {
          // Status change notifications
        }
      );

      if (!isActiveRef.current) return;

      updateState({
        error: null,
        retryCount: 0,
        lastUpdated: new Date(),
      });

      // Reset interval on successful poll
      currentIntervalRef.current = finalConfig.interval;

      // Notify parent component
      onStatusUpdate(analysis);

      // Stop polling if analysis is complete or failed
      if (analysis.status === 'COMPLETED' || analysis.status === 'FAILED') {
        updateState({ isPolling: false });
        return;
      }

      // Schedule next poll
      if (state.isPolling && isActiveRef.current) {
        const nextInterval = currentIntervalRef.current;
        startCountdown(nextInterval);
        
        timeoutRef.current = setTimeout(() => {
          if (isActiveRef.current) {
            pollStatus();
          }
        }, nextInterval);
      }
    } catch (error) {
      if (!isActiveRef.current) return;

      const newRetryCount = state.retryCount + 1;
      const errorMessage = error instanceof ApiError ? error.message : 'Failed to poll status';

      updateState({
        error: errorMessage,
        retryCount: newRetryCount,
      });

      // Stop polling if max retries exceeded
      if (newRetryCount >= finalConfig.maxRetries) {
        updateState({ isPolling: false });
        return;
      }

      // Calculate backoff interval
      const nextInterval = calculateNextInterval(newRetryCount);
      currentIntervalRef.current = nextInterval;

      // Schedule retry with backoff
      if (state.isPolling && isActiveRef.current) {
        startCountdown(nextInterval);
        
        timeoutRef.current = setTimeout(() => {
          if (isActiveRef.current) {
            pollStatus();
          }
        }, nextInterval);
      }
    }
  }, [
    analysisId,
    finalConfig.enabled,
    finalConfig.maxRetries,
    state.isPolling,
    state.retryCount,
    onStatusUpdate,
    updateState,
    calculateNextInterval,
    startCountdown,
  ]);

  const startPolling = useCallback(() => {
    if (!analysisId || state.isPolling) return;

    updateState({
      isPolling: true,
      error: null,
      retryCount: 0,
    });

    currentIntervalRef.current = finalConfig.interval;
    pollStatus();
  }, [analysisId, state.isPolling, finalConfig.interval, pollStatus, updateState]);

  const stopPolling = useCallback(() => {
    updateState({ isPolling: false, nextPollIn: 0 });
    
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
  }, [updateState]);

  const forceRefresh = useCallback(async () => {
    if (!analysisId) return;

    // Stop current polling
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);

    // Reset retry count and poll immediately
    updateState({ retryCount: 0, error: null });
    currentIntervalRef.current = finalConfig.interval;
    
    await pollStatus();
  }, [analysisId, finalConfig.interval, pollStatus, updateState]);

  // Auto-start polling when analysis ID is provided and enabled
  useEffect(() => {
    if (analysisId && finalConfig.enabled && !state.isPolling) {
      startPolling();
    } else if (!analysisId || !finalConfig.enabled) {
      stopPolling();
    }
  }, [analysisId, finalConfig.enabled, state.isPolling, startPolling, stopPolling]);

  // Cleanup timeouts when config changes
  useEffect(() => {
    currentIntervalRef.current = finalConfig.interval;
  }, [finalConfig.interval]);

  return {
    ...state,
    startPolling,
    stopPolling,
    forceRefresh,
    config: finalConfig,
  };
}