'use client';

import { Loader2, Clock, CheckCircle, AlertCircle, Wifi, WifiOff } from 'lucide-react';

interface LoadingStateProps {
  status: string;
  progress?: number;
  message?: string;
  isConnected?: boolean;
  retryCount?: number;
  nextPollIn?: number;
  onRetry?: () => void;
  onCancel?: () => void;
}

export default function LoadingState({ 
  status, 
  progress, 
  message, 
  isConnected = true,
  retryCount = 0,
  nextPollIn = 0,
  onRetry,
  onCancel
}: LoadingStateProps) {
  const getStatusIcon = () => {
    if (!isConnected) {
      return <WifiOff className="h-12 w-12 text-red-400" />;
    }

    switch (status) {
      case 'PENDING':
        return <Clock className="h-12 w-12 text-yellow-400" />;
      case 'PROCESSING':
        return <Loader2 className="h-12 w-12 text-purple-400 animate-spin" />;
      case 'COMPLETED':
        return <CheckCircle className="h-12 w-12 text-green-400" />;
      case 'FAILED':
        return <AlertCircle className="h-12 w-12 text-red-400" />;
      default:
        return <Loader2 className="h-12 w-12 text-gray-400 animate-spin" />;
    }
  };

  const getStatusMessage = () => {
    if (!isConnected) {
      return 'Connection lost - waiting to reconnect...';
    }

    if (message) return message;
    
    switch (status) {
      case 'PENDING':
        return 'Analysis queued...';
      case 'PROCESSING':
        return 'Processing reviews and generating insights...';
      case 'COMPLETED':
        return 'Analysis complete!';
      case 'FAILED':
        return 'Analysis failed';
      default:
        return 'Loading...';
    }
  };

  const getProgressColor = () => {
    if (!isConnected) return 'bg-red-500';
    
    switch (status) {
      case 'PENDING':
        return 'bg-yellow-500';
      case 'PROCESSING':
        return 'bg-blue-600';
      case 'COMPLETED':
        return 'bg-green-500';
      case 'FAILED':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const formatTime = (ms: number): string => {
    const seconds = Math.ceil(ms / 1000);
    return `${seconds}s`;
  };

  return (
    <div className="card-dark p-8 relative z-10">
      <div className="flex flex-col items-center justify-center py-8 space-y-6">
        <div className="relative">
          {getStatusIcon()}
          <div className="absolute inset-0 animate-ping opacity-25">
            {getStatusIcon()}
          </div>
        </div>
        
        <div className="text-center space-y-4 max-w-md">
          <h3 className="text-xl font-semibold text-white">
            {getStatusMessage()}
          </h3>
          
          {/* Progress Bar */}
          {progress !== undefined && (
            <div className="w-80 bg-gray-700 rounded-full h-4 relative overflow-hidden">
              <div 
                className={`h-4 rounded-full transition-all duration-500 bg-gradient-to-r from-purple-500 to-blue-500 relative`}
                style={{ width: `${Math.min(progress, 100)}%` }}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse"></div>
              </div>
              {progress > 0 && (
                <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold text-white">
                  {Math.round(progress)}%
                </span>
              )}
            </div>
          )}

          {/* Connection Status */}
          {!isConnected && (
            <div className="flex items-center justify-center space-x-2 text-red-300 bg-red-900/30 border border-red-500/50 px-4 py-3 rounded-lg">
              <WifiOff className="h-4 w-4" />
              <span className="text-sm">No internet connection</span>
            </div>
          )}

          {/* Retry Information */}
          {retryCount > 0 && (
            <div className="text-sm text-gray-300 bg-gray-800/50 px-4 py-3 rounded-lg border border-gray-600">
              Retry attempt {retryCount} of 5
              {nextPollIn > 0 && (
                <span className="block text-xs text-gray-400 mt-1">
                  Next attempt in {formatTime(nextPollIn)}
                </span>
              )}
            </div>
          )}

          {/* Status-specific messages */}
          <div className="text-sm text-gray-400 space-y-2">
            {status === 'PENDING' && (
              <p>Your analysis is in the queue and will start shortly</p>
            )}
            {status === 'PROCESSING' && (
              <p>This may take a few minutes depending on the number of reviews</p>
            )}
            {status === 'FAILED' && (
              <p>Something went wrong during the analysis process</p>
            )}
            {!isConnected && (
              <p>Please check your internet connection</p>
            )}
          </div>

          {/* Action Buttons */}
          {(status === 'FAILED' || !isConnected) && (
            <div className="flex space-x-3 pt-4">
              {onRetry && (
                <button
                  onClick={onRetry}
                  disabled={!isConnected}
                  className="btn-primary"
                >
                  Try Again
                </button>
              )}
              {onCancel && (
                <button
                  onClick={onCancel}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              )}
            </div>
          )}

          {/* Real-time status indicator */}
          {isConnected && (status === 'PENDING' || status === 'PROCESSING') && (
            <div className="flex items-center justify-center space-x-2 text-green-400 text-sm">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span>Live updates enabled</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}