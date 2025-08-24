'use client';

import { useState } from 'react';
import { Wifi, WifiOff, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';

export default function ConnectionStatus() {
  const [networkStatus, networkActions] = useNetworkStatus();
  const [isExpanded, setIsExpanded] = useState(false);

  const getStatusColor = () => {
    if (!networkStatus.isOnline) return 'text-red-300 bg-red-900/30 border-red-500/50';
    if (!networkStatus.isConnected) return 'text-orange-300 bg-orange-900/30 border-orange-500/50';
    return 'text-green-300 bg-green-900/30 border-green-500/50';
  };

  const getStatusIcon = () => {
    if (!networkStatus.isOnline || !networkStatus.isConnected) {
      return <WifiOff className="h-4 w-4" />;
    }
    return <Wifi className="h-4 w-4" />;
  };

  const getStatusText = () => {
    if (!networkStatus.isOnline) return 'Offline';
    if (!networkStatus.isConnected) return 'Server Unreachable';
    return 'Connected';
  };

  const formatLatency = (latency: number | null) => {
    if (latency === null) return 'Unknown';
    if (latency < 100) return `${latency}ms (Excellent)`;
    if (latency < 300) return `${latency}ms (Good)`;
    if (latency < 1000) return `${latency}ms (Fair)`;
    return `${latency}ms (Poor)`;
  };

  const formatLastChecked = (date: Date | null) => {
    if (!date) return 'Never';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return date.toLocaleTimeString();
  };

  if (networkStatus.isOnline && networkStatus.isConnected && !networkStatus.error) {
    return null; // Don't show when everything is working fine
  }

  return (
    <div className={`border rounded-xl p-4 backdrop-blur-sm ${getStatusColor()}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {getStatusIcon()}
          <span className="font-semibold text-sm">{getStatusText()}</span>
          {networkStatus.error && (
            <span className="text-xs opacity-75">- {networkStatus.error}</span>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={networkActions.checkConnection}
            className="p-2 hover:bg-white hover:bg-opacity-10 rounded-lg transition-colors"
            title="Check connection"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 hover:bg-white hover:bg-opacity-10 rounded-lg transition-colors"
            title="Show details"
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-current border-opacity-20 space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="font-semibold">Browser Status:</span>
              <span className="ml-2">{networkStatus.isOnline ? 'Online' : 'Offline'}</span>
            </div>
            <div>
              <span className="font-semibold">Server Status:</span>
              <span className="ml-2">{networkStatus.isConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
            <div>
              <span className="font-semibold">Latency:</span>
              <span className="ml-2">{formatLatency(networkStatus.latency)}</span>
            </div>
            <div>
              <span className="font-semibold">Last Checked:</span>
              <span className="ml-2">{formatLastChecked(networkStatus.lastChecked)}</span>
            </div>
          </div>
          
          {networkStatus.error && (
            <div className="pt-2">
              <span className="font-semibold">Error Details:</span>
              <p className="mt-1 text-sm opacity-75">{networkStatus.error}</p>
            </div>
          )}
          
          <div className="pt-3 flex space-x-3">
            <button
              onClick={networkActions.checkConnection}
              className="px-3 py-2 bg-white bg-opacity-10 rounded-lg text-sm font-medium hover:bg-opacity-20 transition-colors"
            >
              Test Connection
            </button>
            <button
              onClick={() => networkActions.startMonitoring(10000)}
              className="px-3 py-2 bg-white bg-opacity-10 rounded-lg text-sm font-medium hover:bg-opacity-20 transition-colors"
            >
              Monitor (10s)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}