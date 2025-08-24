'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Analysis, AnalysisRequest, AnalysisStatus } from '@/types';
import { apiService, ApiError } from '@/services/api';

export interface AnalysisState {
  // Current analysis data
  currentAnalysis: Analysis | null;
  analysisId: string;
  
  // UI state
  isLoading: boolean;
  error: string;
  isSubmitting: boolean;
  
  // Network state
  isOnline: boolean;
  retryCount: number;
  
  // Progress tracking
  progress: number;
  statusMessage: string;
  
  // Polling state
  isPolling: boolean;
  pollInterval: number;
}

export interface AnalysisActions {
  // Analysis operations
  submitAnalysis: (request: AnalysisRequest) => Promise<void>;
  refreshAnalysis: () => Promise<void>;
  resetAnalysis: () => void;
  
  // Error handling
  retryAnalysis: () => Promise<void>;
  clearError: () => void;
  
  // Progress tracking
  updateProgress: (progress: number, message?: string) => void;
  
  // Polling control
  startPolling: () => void;
  stopPolling: () => void;
  setPollInterval: (interval: number) => void;
}

const INITIAL_STATE: AnalysisState = {
  currentAnalysis: null,
  analysisId: '',
  isLoading: false,
  error: '',
  isSubmitting: false,
  isOnline: true,
  retryCount: 0,
  progress: 0,
  statusMessage: '',
  isPolling: false,
  pollInterval: 2000,
};

export function useAnalysisState(): [AnalysisState, AnalysisActions] {
  const [state, setState] = useState<AnalysisState>(INITIAL_STATE);
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastRequestRef = useRef<AnalysisRequest | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Monitor online status
  useEffect(() => {
    const handleOnline = () => setState(prev => ({ ...prev, isOnline: true }));
    const handleOffline = () => setState(prev => ({ ...prev, isOnline: false }));

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Set initial online status
    setState(prev => ({ ...prev, isOnline: navigator.onLine }));

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const updateState = useCallback((updates: Partial<AnalysisState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  const getProgressFromStatus = useCallback((status: AnalysisStatus): number => {
    switch (status) {
      case 'PENDING': return 10;
      case 'PROCESSING': return 50;
      case 'COMPLETED': return 100;
      case 'FAILED': return 0;
      default: return 0;
    }
  }, []);

  const getStatusMessage = useCallback((analysis: Analysis | null): string => {
    if (!analysis) return '';
    
    const baseMessage = analysis.analysis_type === 'APP' 
      ? 'Analyzing app store reviews...' 
      : 'Analyzing website reviews from multiple platforms...';
    
    switch (analysis.status) {
      case 'PENDING':
        return 'Analysis queued and waiting to start...';
      case 'PROCESSING':
        return baseMessage;
      case 'COMPLETED':
        return `Analysis complete! Found ${analysis.clusters.length} complaint categories.`;
      case 'FAILED':
        return 'Analysis failed to complete.';
      default:
        return baseMessage;
    }
  }, []);

  const pollAnalysisStatus = useCallback(async () => {
    if (!state.analysisId || !state.isOnline) return;

    try {
      const analysis = await apiService.getAnalysis(state.analysisId);
      const progress = getProgressFromStatus(analysis.status);
      const statusMessage = getStatusMessage(analysis);

      updateState({
        currentAnalysis: analysis,
        progress,
        statusMessage,
        error: '', // Clear any previous errors on successful poll
      });

      // Stop polling if analysis is complete or failed
      if (analysis.status === 'COMPLETED' || analysis.status === 'FAILED') {
        updateState({
          isLoading: false,
          isPolling: false,
        });
        
        if (pollTimeoutRef.current) {
          clearTimeout(pollTimeoutRef.current);
          pollTimeoutRef.current = null;
        }
      }
    } catch (error) {
      console.error('Polling error:', error);
      // Don't update error state for polling failures to avoid spam
      // Just log and continue polling
    }
  }, [state.analysisId, state.isOnline, getProgressFromStatus, getStatusMessage, updateState]);

  const startPolling = useCallback(() => {
    if (state.isPolling || !state.analysisId) return;

    updateState({ isPolling: true });

    const poll = async () => {
      await pollAnalysisStatus();
      
      if (state.isPolling && state.currentAnalysis?.status !== 'COMPLETED' && state.currentAnalysis?.status !== 'FAILED') {
        pollTimeoutRef.current = setTimeout(poll, state.pollInterval);
      }
    };

    poll();
  }, [state.isPolling, state.analysisId, state.pollInterval, state.currentAnalysis?.status, pollAnalysisStatus, updateState]);

  const stopPolling = useCallback(() => {
    updateState({ isPolling: false });
    
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  }, [updateState]);

  const setPollInterval = useCallback((interval: number) => {
    updateState({ pollInterval: Math.max(1000, interval) }); // Minimum 1 second
  }, [updateState]);

  const submitAnalysis = useCallback(async (request: AnalysisRequest) => {
    if (!state.isOnline) {
      throw new ApiError(0, 'No internet connection. Please check your connection and try again.');
    }

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    lastRequestRef.current = request;

    updateState({
      isLoading: true,
      isSubmitting: true,
      error: '',
      retryCount: 0,
      progress: 0,
      statusMessage: 'Starting analysis...',
    });

    try {
      const response = await apiService.submitAnalysis(request);
      
      // Create initial analysis object
      const initialAnalysis: Analysis = {
        id: response.analysis_id,
        app_id: request.analysis_type === 'APP' ? request.input : undefined,
        website_url: request.analysis_type === 'WEBSITE' ? request.input : undefined,
        analysis_type: request.analysis_type,
        status: 'PENDING',
        total_reviews: 0,
        negative_reviews: 0,
        clusters: [],
        created_at: new Date().toISOString(),
      };

      updateState({
        analysisId: response.analysis_id,
        currentAnalysis: initialAnalysis,
        isSubmitting: false,
        progress: 10,
        statusMessage: getStatusMessage(initialAnalysis),
      });

      // Start polling for status updates
      startPolling();
    } catch (error) {
      updateState({
        isLoading: false,
        isSubmitting: false,
        error: error instanceof ApiError ? error.message : 'Failed to start analysis',
      });
      throw error;
    }
  }, [state.isOnline, getStatusMessage, updateState, startPolling]);

  const refreshAnalysis = useCallback(async () => {
    if (!state.analysisId || !state.isOnline) return;

    try {
      const analysis = await apiService.getAnalysis(state.analysisId);
      const progress = getProgressFromStatus(analysis.status);
      const statusMessage = getStatusMessage(analysis);

      updateState({
        currentAnalysis: analysis,
        progress,
        statusMessage,
        error: '',
      });
    } catch (error) {
      updateState({
        error: error instanceof ApiError ? error.message : 'Failed to refresh analysis',
      });
    }
  }, [state.analysisId, state.isOnline, getProgressFromStatus, getStatusMessage, updateState]);

  const retryAnalysis = useCallback(async () => {
    if (!lastRequestRef.current || !state.isOnline) return;

    const newRetryCount = state.retryCount + 1;
    if (newRetryCount > 3) {
      updateState({
        error: 'Maximum retry attempts reached. Please wait a moment before trying again.',
      });
      return;
    }

    updateState({
      retryCount: newRetryCount,
      error: '',
    });

    try {
      await submitAnalysis(lastRequestRef.current);
    } catch (error) {
      // Error is already handled in submitAnalysis
    }
  }, [state.retryCount, state.isOnline, submitAnalysis, updateState]);

  const resetAnalysis = useCallback(() => {
    stopPolling();
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    lastRequestRef.current = null;
    setState(INITIAL_STATE);
  }, [stopPolling]);

  const clearError = useCallback(() => {
    updateState({ error: '' });
  }, [updateState]);

  const updateProgress = useCallback((progress: number, message?: string) => {
    updateState({
      progress: Math.max(0, Math.min(100, progress)),
      statusMessage: message || state.statusMessage,
    });
  }, [state.statusMessage, updateState]);

  // Auto-start polling when analysis ID is set
  useEffect(() => {
    if (state.analysisId && !state.isPolling && state.currentAnalysis?.status !== 'COMPLETED' && state.currentAnalysis?.status !== 'FAILED') {
      startPolling();
    }
  }, [state.analysisId, state.isPolling, state.currentAnalysis?.status, startPolling]);

  const actions: AnalysisActions = {
    submitAnalysis,
    refreshAnalysis,
    resetAnalysis,
    retryAnalysis,
    clearError,
    updateProgress,
    startPolling,
    stopPolling,
    setPollInterval,
  };

  return [state, actions];
}