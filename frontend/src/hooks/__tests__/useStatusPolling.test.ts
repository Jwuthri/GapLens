import { renderHook, act } from '@testing-library/react';
import { useStatusPolling } from '../useStatusPolling';

// Mock the API service
jest.mock('@/services/api', () => ({
  getAnalysisStatus: jest.fn(),
}));

import { getAnalysisStatus } from '@/services/api';

const mockGetAnalysisStatus = getAnalysisStatus as jest.MockedFunction<typeof getAnalysisStatus>;

describe('useStatusPolling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('starts polling when analysis ID is provided', async () => {
    mockGetAnalysisStatus.mockResolvedValue({
      analysis_id: 'test-id',
      status: 'processing',
      progress: 50,
      message: 'Processing reviews...',
    });

    const { result } = renderHook(() => useStatusPolling('test-id'));

    expect(result.current.status).toBe('pending');
    expect(result.current.progress).toBe(0);

    // Fast-forward to trigger the first poll
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    expect(mockGetAnalysisStatus).toHaveBeenCalledWith('test-id');
  });

  it('stops polling when status becomes completed', async () => {
    mockGetAnalysisStatus
      .mockResolvedValueOnce({
        analysis_id: 'test-id',
        status: 'processing',
        progress: 50,
        message: 'Processing reviews...',
      })
      .mockResolvedValueOnce({
        analysis_id: 'test-id',
        status: 'completed',
        progress: 100,
        message: 'Analysis completed',
      });

    const { result } = renderHook(() => useStatusPolling('test-id'));

    // First poll
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    expect(result.current.status).toBe('processing');
    expect(result.current.progress).toBe(50);

    // Second poll
    await act(async () => {
      jest.advanceTimersByTime(2000);
    });

    expect(result.current.status).toBe('completed');
    expect(result.current.progress).toBe(100);

    // Should not poll again
    mockGetAnalysisStatus.mockClear();
    await act(async () => {
      jest.advanceTimersByTime(5000);
    });

    expect(mockGetAnalysisStatus).not.toHaveBeenCalled();
  });

  it('stops polling when status becomes failed', async () => {
    mockGetAnalysisStatus.mockResolvedValue({
      analysis_id: 'test-id',
      status: 'failed',
      progress: 0,
      message: 'Analysis failed',
      error: 'Processing error occurred',
    });

    const { result } = renderHook(() => useStatusPolling('test-id'));

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    expect(result.current.status).toBe('failed');
    expect(result.current.error).toBe('Processing error occurred');

    // Should not poll again
    mockGetAnalysisStatus.mockClear();
    await act(async () => {
      jest.advanceTimersByTime(5000);
    });

    expect(mockGetAnalysisStatus).not.toHaveBeenCalled();
  });

  it('handles API errors gracefully', async () => {
    mockGetAnalysisStatus.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useStatusPolling('test-id'));

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    expect(result.current.error).toBe('Failed to fetch analysis status');
  });

  it('does not start polling without analysis ID', () => {
    const { result } = renderHook(() => useStatusPolling(null));

    expect(result.current.status).toBe('pending');
    expect(mockGetAnalysisStatus).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(mockGetAnalysisStatus).not.toHaveBeenCalled();
  });

  it('restarts polling when analysis ID changes', async () => {
    mockGetAnalysisStatus.mockResolvedValue({
      analysis_id: 'test-id-1',
      status: 'processing',
      progress: 25,
      message: 'Processing...',
    });

    const { result, rerender } = renderHook(
      ({ analysisId }) => useStatusPolling(analysisId),
      { initialProps: { analysisId: 'test-id-1' } }
    );

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    expect(mockGetAnalysisStatus).toHaveBeenCalledWith('test-id-1');

    // Change analysis ID
    mockGetAnalysisStatus.mockClear();
    mockGetAnalysisStatus.mockResolvedValue({
      analysis_id: 'test-id-2',
      status: 'pending',
      progress: 0,
      message: 'Queued for processing',
    });

    rerender({ analysisId: 'test-id-2' });

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    expect(mockGetAnalysisStatus).toHaveBeenCalledWith('test-id-2');
  });

  it('cleans up polling on unmount', async () => {
    mockGetAnalysisStatus.mockResolvedValue({
      analysis_id: 'test-id',
      status: 'processing',
      progress: 50,
      message: 'Processing...',
    });

    const { unmount } = renderHook(() => useStatusPolling('test-id'));

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    expect(mockGetAnalysisStatus).toHaveBeenCalledTimes(1);

    unmount();

    // Should not continue polling after unmount
    mockGetAnalysisStatus.mockClear();
    await act(async () => {
      jest.advanceTimersByTime(5000);
    });

    expect(mockGetAnalysisStatus).not.toHaveBeenCalled();
  });

  it('uses exponential backoff for polling interval', async () => {
    mockGetAnalysisStatus.mockResolvedValue({
      analysis_id: 'test-id',
      status: 'processing',
      progress: 50,
      message: 'Processing...',
    });

    renderHook(() => useStatusPolling('test-id'));

    // First poll should happen after 1 second
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(mockGetAnalysisStatus).toHaveBeenCalledTimes(1);

    // Second poll should happen after 2 seconds
    mockGetAnalysisStatus.mockClear();
    await act(async () => {
      jest.advanceTimersByTime(2000);
    });
    expect(mockGetAnalysisStatus).toHaveBeenCalledTimes(1);

    // Third poll should happen after 4 seconds
    mockGetAnalysisStatus.mockClear();
    await act(async () => {
      jest.advanceTimersByTime(4000);
    });
    expect(mockGetAnalysisStatus).toHaveBeenCalledTimes(1);
  });

  it('resets polling interval when status changes', async () => {
    mockGetAnalysisStatus
      .mockResolvedValueOnce({
        analysis_id: 'test-id',
        status: 'pending',
        progress: 0,
        message: 'Queued',
      })
      .mockResolvedValueOnce({
        analysis_id: 'test-id',
        status: 'processing',
        progress: 25,
        message: 'Processing started',
      });

    renderHook(() => useStatusPolling('test-id'));

    // First poll
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    // Status changed, so interval should reset
    await act(async () => {
      jest.advanceTimersByTime(1000); // Should poll again after 1 second, not 2
    });

    expect(mockGetAnalysisStatus).toHaveBeenCalledTimes(2);
  });

  it('provides correct loading state', async () => {
    mockGetAnalysisStatus.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({
        analysis_id: 'test-id',
        status: 'processing',
        progress: 50,
        message: 'Processing...',
      }), 100))
    );

    const { result } = renderHook(() => useStatusPolling('test-id'));

    expect(result.current.isLoading).toBe(false);

    // Start polling
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(result.current.isLoading).toBe(true);

    // Complete the API call
    await act(async () => {
      jest.advanceTimersByTime(100);
    });

    expect(result.current.isLoading).toBe(false);
  });

  it('handles rapid status updates correctly', async () => {
    const statusUpdates = [
      { status: 'pending', progress: 0, message: 'Queued' },
      { status: 'processing', progress: 25, message: 'Scraping reviews' },
      { status: 'processing', progress: 50, message: 'Processing text' },
      { status: 'processing', progress: 75, message: 'Clustering complaints' },
      { status: 'completed', progress: 100, message: 'Analysis complete' },
    ];

    let callCount = 0;
    mockGetAnalysisStatus.mockImplementation(() => {
      const update = statusUpdates[callCount] || statusUpdates[statusUpdates.length - 1];
      callCount++;
      return Promise.resolve({
        analysis_id: 'test-id',
        ...update,
      });
    });

    const { result } = renderHook(() => useStatusPolling('test-id'));

    // Process all status updates
    for (let i = 0; i < statusUpdates.length; i++) {
      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      const expectedUpdate = statusUpdates[i];
      expect(result.current.status).toBe(expectedUpdate.status);
      expect(result.current.progress).toBe(expectedUpdate.progress);
      expect(result.current.message).toBe(expectedUpdate.message);

      if (expectedUpdate.status === 'completed') {
        break; // Polling should stop
      }
    }

    // Verify polling stopped after completion
    mockGetAnalysisStatus.mockClear();
    await act(async () => {
      jest.advanceTimersByTime(5000);
    });
    expect(mockGetAnalysisStatus).not.toHaveBeenCalled();
  });
});