-- Widen chat_history text columns for long PDF/RAG replies.
-- Run against an existing chatdb database:
--   Get-Content migrations\schema_chat_history_mediumtext.sql -Raw | mysql -u root -p chatdb

ALTER TABLE chat_history
    MODIFY prompt_text MEDIUMTEXT NOT NULL,
    MODIFY response_text MEDIUMTEXT NOT NULL;
