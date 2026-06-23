-- ChatOff MySQL schema
-- Usage:
--   1. CREATE DATABASE IF NOT EXISTS chatdb;
--   2. USE chatdb;
--   3. SOURCE schema.sql;   (or import via MySQL Workbench)

CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    fullname   VARCHAR(255) NOT NULL,
    username   VARCHAR(100) NOT NULL UNIQUE,
    email      VARCHAR(255) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    must_change_password TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_history (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT          NOT NULL,
    session_id    VARCHAR(36)  NOT NULL,
    session_title VARCHAR(255) NOT NULL,
    prompt_text   MEDIUMTEXT   NOT NULL,
    response_text MEDIUMTEXT   NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_session (user_id, session_id),
    CONSTRAINT fk_chat_history_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_topics (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    parent_id     INT NULL,
    topic_name    VARCHAR(255) NOT NULL,
    reply_message TEXT         NOT NULL,
    pdf_source    VARCHAR(255) NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parent (parent_id),
    CONSTRAINT fk_chat_topics_parent
        FOREIGN KEY (parent_id) REFERENCES chat_topics(id) ON DELETE CASCADE
);

-- Legacy knowledge table (kept for compatibility with auth.py helpers)
CREATE TABLE IF NOT EXISTS `option` (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    title      VARCHAR(255) NOT NULL,
    content    TEXT         NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
