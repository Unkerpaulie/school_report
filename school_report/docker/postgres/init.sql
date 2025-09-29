-- PostgreSQL initialization script for development
-- This script runs when the PostgreSQL container starts for the first time

-- Create additional databases if needed
-- CREATE DATABASE school_report_test;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE school_report_dev TO school_admin;

-- Create extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Log initialization
SELECT 'PostgreSQL initialized for school_report development' as message;
