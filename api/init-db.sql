-- Creates the test database alongside the dev database.
-- Mounted into /docker-entrypoint-initdb.d/ so it runs on first container start.
-- The dev database (paypredict_dev) is created by POSTGRES_DB env var.

CREATE DATABASE paypredict_test OWNER paypredict;
