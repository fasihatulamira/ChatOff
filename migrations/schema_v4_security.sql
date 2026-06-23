-- Phase 4: bcrypt passwords + forced password change flag
-- Run against an existing chatdb database:
--   Get-Content migrations\schema_v4_security.sql -Raw | mysql -u root -p chatdb

ALTER TABLE users MODIFY password VARCHAR(255) NOT NULL;

-- Skip if column already exists (ensure_schema in auth.py handles this automatically).
ALTER TABLE users
    ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 0;

UPDATE users SET must_change_password = 1 WHERE username = 'admin';
