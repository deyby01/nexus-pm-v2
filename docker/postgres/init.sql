-- NexusPM Enterprise Database Initialization
-- This script runs automatically when PostgreSQL container starts

-- Create necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For composite indexes

-- Set timezone
SET timezone = 'UTC';

-- Create custom functions for common operations
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Log initialization
DO $$ 
BEGIN 
    RAISE NOTICE '✅ NexusPM Enterprise database initialized successfully';
    RAISE NOTICE '📦 Extensions installed: uuid-ossp, pg_trgm, btree_gin';
    RAISE NOTICE '🕐 Timezone set to: UTC';
    RAISE NOTICE '⚡ Custom functions created for automated triggers';
END $$;