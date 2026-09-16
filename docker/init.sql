-- SmartVerify Database Initialization
-- Tables are created by SQLAlchemy on startup; this script
-- seeds an admin user and default loan officer.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- The application ORM will create all tables.
-- Seed data will be inserted via the API on first login.
