"""Performance monitoring and logging service."""

import time
import logging
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from functools import wraps
from collections import defaultdict, deque

from .cache_service import cache_service


class PerformanceMonitor:
    """Performance monitoring service for tracking application metrics."""
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize the performance monitor.
        
        Args:
            max_history: Maximum number of performance records to keep in memory
        """
        self.logger = logging.getLogger(__name__)
        self.max_history = max_history
        
        # Performance metrics storage
        self._metrics = defaultdict(deque)
        self._lock = threading.Lock()
        
        # System metrics
        self._system_metrics = deque(maxlen=100)  # Keep last 100 system snapshots
        
        # Start background monitoring
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_system_metrics, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_system_metrics(self):
        """Background thread to monitor system metrics."""
        while self._monitoring_active:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                system_metric = {
                    'timestamp': datetime.now(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_percent': disk.percent,
                    'disk_used_gb': disk.used / (1024**3),
                    'disk_free_gb': disk.free / (1024**3)
                }
                
                with self._lock:
                    self._system_metrics.append(system_metric)
                
                # Cache system metrics
                cache_service.set("performance:system_metrics", list(self._system_metrics), ttl=300)
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
            
            time.sleep(60)  # Collect every minute
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring_active = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
    
    @contextmanager
    def measure_time(self, operation_name: str, metadata: Optional[Dict] = None):
        """
        Context manager to measure execution time of operations.
        
        Args:
            operation_name: Name of the operation being measured
            metadata: Additional metadata to store with the measurement
        """
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / (1024**2)  # MB
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / (1024**2)  # MB
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            self.record_performance(
                operation_name=operation_name,
                duration=duration,
                memory_delta=memory_delta,
                metadata=metadata
            )
    
    def record_performance(self, operation_name: str, duration: float, 
                          memory_delta: float = 0, metadata: Optional[Dict] = None):
        """
        Record a performance measurement.
        
        Args:
            operation_name: Name of the operation
            duration: Duration in seconds
            memory_delta: Memory usage change in MB
            metadata: Additional metadata
        """
        record = {
            'timestamp': datetime.now(),
            'operation': operation_name,
            'duration': duration,
            'memory_delta': memory_delta,
            'metadata': metadata or {}
        }
        
        with self._lock:
            self._metrics[operation_name].append(record)
            
            # Limit history size
            if len(self._metrics[operation_name]) > self.max_history:
                self._metrics[operation_name].popleft()
        
        # Log slow operations
        if duration > 10:  # Log operations taking more than 10 seconds
            self.logger.warning(
                f"Slow operation detected: {operation_name} took {duration:.2f}s "
                f"(memory delta: {memory_delta:.2f}MB)"
            )
        
        # Cache recent performance data
        self._cache_performance_data()
    
    def _cache_performance_data(self):
        """Cache recent performance data for API access."""
        try:
            # Get recent metrics (last hour)
            cutoff_time = datetime.now() - timedelta(hours=1)
            recent_metrics = {}
            
            with self._lock:
                for operation, records in self._metrics.items():
                    recent_records = [
                        record for record in records 
                        if record['timestamp'] > cutoff_time
                    ]
                    if recent_records:
                        recent_metrics[operation] = recent_records
            
            cache_service.set("performance:recent_metrics", recent_metrics, ttl=300)
            
        except Exception as e:
            self.logger.error(f"Error caching performance data: {e}")
    
    def get_operation_stats(self, operation_name: str, hours: int = 24) -> Dict:
        """
        Get statistics for a specific operation.
        
        Args:
            operation_name: Name of the operation
            hours: Number of hours to look back
            
        Returns:
            Dictionary containing operation statistics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            records = [
                record for record in self._metrics.get(operation_name, [])
                if record['timestamp'] > cutoff_time
            ]
        
        if not records:
            return {
                'operation': operation_name,
                'count': 0,
                'avg_duration': 0,
                'min_duration': 0,
                'max_duration': 0,
                'total_duration': 0
            }
        
        durations = [record['duration'] for record in records]
        
        return {
            'operation': operation_name,
            'count': len(records),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'total_duration': sum(durations),
            'avg_memory_delta': sum(record['memory_delta'] for record in records) / len(records)
        }
    
    def get_all_operations_stats(self, hours: int = 24) -> List[Dict]:
        """
        Get statistics for all operations.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of operation statistics
        """
        with self._lock:
            operations = list(self._metrics.keys())
        
        return [self.get_operation_stats(op, hours) for op in operations]
    
    def get_system_metrics(self, hours: int = 1) -> List[Dict]:
        """
        Get system metrics for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of system metrics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [
                metric for metric in self._system_metrics
                if metric['timestamp'] > cutoff_time
            ]
    
    def get_performance_summary(self) -> Dict:
        """
        Get a summary of performance metrics.
        
        Returns:
            Dictionary containing performance summary
        """
        # Get recent system metrics
        recent_system = self.get_system_metrics(hours=1)
        
        # Get operation statistics
        operation_stats = self.get_all_operations_stats(hours=24)
        
        # Calculate summary statistics
        if recent_system:
            avg_cpu = sum(m['cpu_percent'] for m in recent_system) / len(recent_system)
            avg_memory = sum(m['memory_percent'] for m in recent_system) / len(recent_system)
            current_system = recent_system[-1]
        else:
            avg_cpu = avg_memory = 0
            current_system = {}
        
        # Find slowest operations
        slowest_ops = sorted(
            [op for op in operation_stats if op['count'] > 0],
            key=lambda x: x['avg_duration'],
            reverse=True
        )[:5]
        
        return {
            'timestamp': datetime.now(),
            'system_metrics': {
                'current_cpu_percent': current_system.get('cpu_percent', 0),
                'current_memory_percent': current_system.get('memory_percent', 0),
                'avg_cpu_percent_1h': round(avg_cpu, 2),
                'avg_memory_percent_1h': round(avg_memory, 2),
                'memory_used_gb': current_system.get('memory_used_gb', 0),
                'disk_used_percent': current_system.get('disk_percent', 0)
            },
            'operation_metrics': {
                'total_operations': len(operation_stats),
                'total_executions_24h': sum(op['count'] for op in operation_stats),
                'slowest_operations': slowest_ops
            },
            'cache_metrics': cache_service.get_cache_stats()
        }


def performance_monitor(operation_name: str, include_memory: bool = True):
    """
    Decorator to monitor performance of functions.
    
    Args:
        operation_name: Name of the operation for monitoring
        include_memory: Whether to track memory usage
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            metadata = {
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_count': len(kwargs)
            }
            
            with monitor.measure_time(operation_name, metadata):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global performance monitor instance
monitor = PerformanceMonitor()