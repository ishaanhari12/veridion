-- Runs automatically when PostgreSQL container starts for the first time.
-- Creates the test database alongside the main one.
CREATE DATABASE veridion_test;
GRANT ALL PRIVILEGES ON DATABASE veridion_test TO veridion;
