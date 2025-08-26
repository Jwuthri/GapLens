-- Production database initialization script
-- This script sets up the database with proper permissions and optimizations

-- Create application database if it doesn't exist
CREATE DATABASE review_gap_analyzer_prod;

-- Connect to the application database
\c review_gap_analyzer_prod;

-- Create application user with limited privileges
CREATE USER app_user WITH PASSWORD 'change_me_in_production';

-- Grant necessary permissions
GRANT CONNECT ON DATABASE review_gap_analyzer_prod TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT CREATE ON SCHEMA public TO app_user;

-- Performance optimizations
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Reload configuration
SELECT pg_reload_conf();