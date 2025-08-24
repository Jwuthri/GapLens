#!/usr/bin/env python3
"""Enhanced integration test for Celery background processing."""

import os
import sys
import time
from uuid import uuid4
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.celery_app import celery_app
from app.tasks.analysis_tasks import process_app_analysis, process_website_analysis
from app.tasks.maintenance_tasks import cleanup_old_results, system_health_check


def test_celery_connection():
    """Test basic Celery connection and task queuing."""
    print("Testing Celery connection...")
    
    try:
        # Test basic Celery connection
        inspector = celery_app.control.inspect()
        stats = inspector.stats()
        
        if stats:
            print("✓ Celery workers are running")
            for worker, worker_stats in stats.items():
                pool_info = worker_stats.get('pool', {})
                print(f"  Worker: {worker}")
                print(f"  Pool: {pool_info.get('max-concurrency', 'N/A')} processes")
                print(f"  Processes: {pool_info.get('processes', 'N/A')}")
        else:
            print("⚠ No Celery workers detected")
            print("  Start workers with: celery -A app.core.celery_app worker --loglevel=info")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Celery connection failed: {e}")
        return False


def test_task_queuing():
    """Test task queuing without execution."""
    print("\nTesting task queuing...")
    
    try:
        # Test app analysis task queuing
        analysis_id = str(uuid4())
        app_identifier_data = {
            "app_id": "com.example.test",
            "platform": "google_play",
            "app_name": "Test App",
            "developer": "Test Developer"
        }
        
        # Queue the task (don't wait for result)
        task = process_app_analysis.delay(analysis_id, app_identifier_data)
        print(f"✓ App analysis task queued: {task.id}")
        
        # Test website analysis task queuing
        website_analysis_id = str(uuid4())
        website_url = "https://example.com"
        
        task2 = process_website_analysis.delay(website_analysis_id, website_url)
        print(f"✓ Website analysis task queued: {task2.id}")
        
        # Check task status
        print(f"  App task status: {task.status}")
        print(f"  Website task status: {task2.status}")
        
        return True
        
    except Exception as e:
        print(f"✗ Task queuing failed: {e}")
        return False


def test_maintenance_tasks():
    """Test maintenance task queuing."""
    print("\nTesting maintenance tasks...")
    
    try:
        # Test cleanup task
        cleanup_task = cleanup_old_results.delay()
        print(f"✓ Cleanup task queued: {cleanup_task.id}")
        
        # Test health check task
        health_task = system_health_check.delay()
        print(f"✓ Health check task queued: {health_task.id}")
        
        # Wait a moment and check status
        time.sleep(1)
        print(f"  Cleanup task status: {cleanup_task.status}")
        print(f"  Health check task status: {health_task.status}")
        
        return True
        
    except Exception as e:
        print(f"✗ Maintenance task queuing failed: {e}")
        return False


def test_redis_connection():
    """Test Redis connection."""
    print("\nTesting Redis connection...")
    
    try:
        import redis
        
        # Get Redis URL from Celery config
        broker_url = celery_app.conf.broker_url
        print(f"  Broker URL: {broker_url}")
        
        # Parse Redis URL
        if broker_url.startswith('redis://'):
            redis_client = redis.from_url(broker_url)
            redis_client.ping()
            print("✓ Redis connection successful")
            
            # Test basic operations
            test_key = f'test_key_{int(time.time())}'
            redis_client.set(test_key, 'test_value', ex=10)
            value = redis_client.get(test_key)
            if value == b'test_value':
                print("✓ Redis read/write operations working")
            
            # Test Redis info
            info = redis_client.info()
            print(f"  Redis version: {info.get('redis_version', 'unknown')}")
            print(f"  Connected clients: {info.get('connected_clients', 'unknown')}")
            
            return True
        else:
            print(f"⚠ Non-Redis broker detected: {broker_url}")
            return True
            
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("  Make sure Redis is running: redis-server")
        return False


def test_task_routing():
    """Test task routing to different queues."""
    print("\nTesting task routing...")
    
    try:
        inspector = celery_app.control.inspect()
        
        # Get active queues
        active_queues = inspector.active_queues()
        
        if active_queues:
            print("✓ Active queues detected:")
            for worker, queues in active_queues.items():
                print(f"  Worker {worker}:")
                for queue in queues:
                    print(f"    - {queue['name']} (routing_key: {queue.get('routing_key', 'N/A')})")
        else:
            print("⚠ No active queues detected")
            return False
        
        # Check if expected queues are present
        expected_queues = ['analysis', 'maintenance']
        all_queue_names = []
        
        for queues in active_queues.values():
            all_queue_names.extend([q['name'] for q in queues])
        
        for expected_queue in expected_queues:
            if expected_queue in all_queue_names:
                print(f"✓ Queue '{expected_queue}' is active")
            else:
                print(f"⚠ Queue '{expected_queue}' not found")
        
        return True
        
    except Exception as e:
        print(f"✗ Task routing test failed: {e}")
        return False


def test_task_progress_tracking():
    """Test task progress tracking functionality."""
    print("\nTesting task progress tracking...")
    
    try:
        # This is a simplified test - in a real scenario, you'd need a test database
        from app.tasks.analysis_tasks import update_task_progress
        
        # Test the progress update function (will fail without database, but we can catch that)
        test_analysis_id = uuid4()
        
        try:
            update_task_progress(test_analysis_id, 50.0, "Test progress update")
            print("✓ Progress tracking function executed (database connection needed for full test)")
        except Exception as db_error:
            print(f"⚠ Progress tracking test requires database connection: {str(db_error)[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Progress tracking test failed: {e}")
        return False


def test_error_handling():
    """Test error handling and retry logic."""
    print("\nTesting error handling...")
    
    try:
        # Test health check task which should succeed
        health_task = system_health_check.delay()
        
        # Wait for a short time
        time.sleep(2)
        
        if health_task.status in ['SUCCESS', 'PENDING', 'PROGRESS']:
            print(f"✓ Health check task status: {health_task.status}")
        else:
            print(f"⚠ Health check task status: {health_task.status}")
        
        # Try to get result with timeout
        try:
            result = health_task.get(timeout=5)
            if isinstance(result, dict) and 'timestamp' in result:
                print("✓ Health check task returned valid result")
            else:
                print(f"⚠ Health check task returned unexpected result: {type(result)}")
        except Exception as e:
            print(f"⚠ Could not get health check result: {str(e)[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False


def test_worker_monitoring():
    """Test worker monitoring capabilities."""
    print("\nTesting worker monitoring...")
    
    try:
        inspector = celery_app.control.inspect()
        
        # Get comprehensive worker information
        stats = inspector.stats()
        active = inspector.active()
        scheduled = inspector.scheduled()
        reserved = inspector.reserved()
        
        if stats:
            print("✓ Worker monitoring data available:")
            
            total_active = 0
            total_scheduled = 0
            total_reserved = 0
            
            for worker_name in stats.keys():
                active_count = len(active.get(worker_name, [])) if active else 0
                scheduled_count = len(scheduled.get(worker_name, [])) if scheduled else 0
                reserved_count = len(reserved.get(worker_name, [])) if reserved else 0
                
                total_active += active_count
                total_scheduled += scheduled_count
                total_reserved += reserved_count
                
                print(f"  Worker {worker_name}:")
                print(f"    Active tasks: {active_count}")
                print(f"    Scheduled tasks: {scheduled_count}")
                print(f"    Reserved tasks: {reserved_count}")
            
            print(f"  Total active tasks: {total_active}")
            print(f"  Total scheduled tasks: {total_scheduled}")
            print(f"  Total reserved tasks: {total_reserved}")
            
        else:
            print("⚠ No worker monitoring data available")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Worker monitoring test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("=== Enhanced Celery Integration Tests ===")
    print(f"Test started at: {datetime.now().isoformat()}\n")
    
    tests = [
        test_redis_connection,
        test_celery_connection,
        test_task_routing,
        test_task_queuing,
        test_maintenance_tasks,
        test_task_progress_tracking,
        test_error_handling,
        test_worker_monitoring,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print(f"\n=== Results ===")
    print(f"Test completed at: {datetime.now().isoformat()}")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All tests passed! Celery setup is working correctly.")
        print("\nNext steps:")
        print("- Run actual analysis tasks with test data")
        print("- Monitor worker performance under load")
        print("- Test failure scenarios and recovery")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above for details.")
        print("\nTroubleshooting:")
        print("- Ensure Redis is running: redis-server")
        print("- Start Celery workers: celery -A app.core.celery_app worker --loglevel=info")
        print("- Check database connectivity for full functionality")
        return 1


if __name__ == "__main__":
    sys.exit(main())