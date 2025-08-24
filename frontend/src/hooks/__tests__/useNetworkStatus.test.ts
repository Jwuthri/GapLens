import { renderHook, act } from '@testing-library/react';
import { useNetworkStatus } from '../useNetworkStatus';
import { apiService } from '../../services/api';

// Mock the API service
jest.mock('../../services/api');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

// Mock navigator.onLine
Object.defineProperty(navigator, 'onLine', {
  writable: true,
  value: true,
});

describe('useNetworkStatus', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true,
    });
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useNetworkStatus());
    const [status] = result.current;

    expect(status.isOnline).toBe(true);
    expect(status.isConnected).toBe(true);
    expect(status.latency).toBeNull();
    expect(status.lastChecked).toBeNull();
    expect(status.error).toBeNull();
  });

  it('should check connection successfully', async () => {
    mockApiService.testConnection.mockResolvedValue({
      isConnected: true,
      latency: 100,
    });

    const { result } = renderHook(() => useNetworkStatus());
    const [, actions] = result.current;

    await act(async () => {
      await actions.checkConnection();
    });

    const [status] = result.current;
    expect(status.isConnected).toBe(true);
    expect(status.latency).toBe(100);
    expect(status.lastChecked).not.toBeNull();
    expect(status.error).toBeNull();
  });

  it('should handle connection failure', async () => {
    mockApiService.testConnection.mockResolvedValue({
      isConnected: false,
      latency: 5000,
      error: 'Connection timeout',
    });

    const { result } = renderHook(() => useNetworkStatus());
    const [, actions] = result.current;

    await act(async () => {
      await actions.checkConnection();
    });

    const [status] = result.current;
    expect(status.isConnected).toBe(false);
    expect(status.latency).toBe(5000);
    expect(status.error).toBe('Connection timeout');
  });

  it('should handle offline state', () => {
    // Simulate going offline
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: false,
    });

    const { result } = renderHook(() => useNetworkStatus());

    // Simulate offline event
    act(() => {
      window.dispatchEvent(new Event('offline'));
    });

    const [status] = result.current;
    expect(status.isOnline).toBe(false);
    expect(status.isConnected).toBe(false);
    expect(status.error).toBe('Device is offline');
  });

  it('should handle online state', () => {
    // Start offline
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: false,
    });

    const { result } = renderHook(() => useNetworkStatus());

    // Go back online
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true,
    });

    act(() => {
      window.dispatchEvent(new Event('online'));
    });

    const [status] = result.current;
    expect(status.isOnline).toBe(true);
  });
});