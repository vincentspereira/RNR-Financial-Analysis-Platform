-- Financial Analysis Platform - Database Initialization
-- This script runs on first container start

-- Required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant permissions to application user
-- Note: Replace 'financial_app' with actual user from environment
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'financial_app') THEN
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO financial_app;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO financial_app;
        GRANT USAGE ON SCHEMA public TO financial_app;
    END IF;
END
$$;

-- Ensure future objects get correct permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
