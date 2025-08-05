-- Script to initialize PostgreSQL database for Eva AI
-- Run this as postgres superuser

-- Create the database if it doesn't exist
SELECT 'CREATE DATABASE eva_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'eva_db')\gexec

-- Connect to eva_db
\c eva_db

-- Create user if it doesn't exist
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'eva_user') THEN

      CREATE ROLE eva_user WITH LOGIN PASSWORD 'eva_secure_password_2025!';
   END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE eva_db TO eva_user;

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant usage on schema
GRANT ALL ON SCHEMA public TO eva_user;

-- Grant all privileges on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO eva_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO eva_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO eva_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO eva_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO eva_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO eva_user;