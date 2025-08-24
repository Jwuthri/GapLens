import { renderHook, act } from '@testing-library/react';
import { useAnalysisState } from '../useAnalysisState';
import { apiService } from '../../services/api';

// Mock the API service
jest.mock('../../services/api');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

// Mock navigator.onLine
Object.defineProperty(navigator, 'onLine', {
  writable: true,
  value: true,
});

describe('useAnalysisState', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true,
    });
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useAnalysisState());
    const [state] = result.current;

    expect(state.currentAnalysis).toBeNull();
    expect(state.analysisId).toBe('');
    expect(state.isLoading).toBe(false);
    expect(state.error).toBe('');
    expect(state.isSubmitting).toBe(false);
    expect(state.retryCount).toBe(0);
    expect(state.progress).toBe(0);
  });

  it('should handle successful analysis submission', async () => {
    mockApiService.submitAnalysis.mockResolvedValue({ analysis_id: 'test-id' });

    const { result } = renderHook(() => useAnalysisState());
    const [, actions] = result.current;

    await act(async () => {
      await actions.submitAnalysis({
        input: 'test-app-id',
        analysis_type: 'APP',
      });
    });

    const [state] = result.current;
    expect(state.analysisId).toBe('test-id');
    expect(state.currentAnalysis).not.toBeNull();
    expect(state.currentAnalysis?.status).toBe('PENDING');
    expect(state.isSubmitting).toBe(false);
  });

  it('should handle analysis submission error', async () => {
    const error = new Error('Submission failed');
    mockApiService.submitAnalysis.mockRejectedValue(error);

    const { result } = renderHook(() => useAnalysisState());
    const [, actions] = result.current;

    await act(async () => {
      try {
        await actions.submitAnalysis({
          input: 'test-app-id',
          analysis_type: 'APP',
        });
      } catch (e) {
        // Expected to throw
      }
    });

    const [state] = result.current;
    expect(state.error).toBe('Failed to start analysis');
    expect(state.isLoading).toBe(false);
    expect(state.isSubmitting).toBe(false);
  });

  it('should reset analysis state', () => {
    const { result } = renderHook(() => useAnalysisState());
    const [, actions] = result.current;

    act(() => {
      actions.resetAnalysis();
    });

    const [state] = result.current;
    expect(state.currentAnalysis).toBeNull();
    expect(state.analysisId).toBe('');
    expect(state.error).toBe('');
    expect(state.retryCount).toBe(0);
  });

  it('should update progress', () => {
    const { result } = renderHook(() => useAnalysisState());
    const [, actions] = result.current;

    act(() => {
      actions.updateProgress(50, 'Processing...');
    });

    const [state] = result.current;
    expect(state.progress).toBe(50);
    expect(state.statusMessage).toBe('Processing...');
  });

  it('should clear error', () => {
    const { result } = renderHook(() => useAnalysisState());
    const [, actions] = result.current;

    act(() => {
      actions.clearError();
    });

    const [state] = result.current;
    expect(state.error).toBe('');
  });
});