-- Remove legacy option table (knowledge base now uses RAG JSON store).
-- Run against an existing chatdb database:
--   Get-Content migrations\schema_drop_option.sql -Raw | mysql -u root -p chatdb

DROP TABLE IF EXISTS `option`;
