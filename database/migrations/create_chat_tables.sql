-- Migration script to create chat session and message tables
-- Run this script in your MySQL database

CREATE TABLE IF NOT EXISTS `chat_sessions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `session_id` VARCHAR(255) NOT NULL UNIQUE,
  `user_id` BIGINT UNSIGNED NULL,
  `email` VARCHAR(255) NULL,
  `name` VARCHAR(255) NULL,
  `browser_fingerprint` VARCHAR(255) NULL,
  `ip_address` VARCHAR(45) NULL,
  `user_agent` VARCHAR(500) NULL,
  `status` VARCHAR(50) DEFAULT 'active',
  `metadata` JSON NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_message_at` DATETIME NULL,
  INDEX `idx_session_id` (`session_id`),
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_email` (`email`),
  INDEX `idx_browser_fingerprint` (`browser_fingerprint`),
  INDEX `idx_status` (`status`),
  INDEX `idx_session_user` (`session_id`, `user_id`),
  INDEX `idx_session_email` (`session_id`, `email`),
  INDEX `idx_session_fingerprint` (`session_id`, `browser_fingerprint`),
  FOREIGN KEY (`user_id`) REFERENCES `users2`(`Id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `session_id` VARCHAR(255) NOT NULL,
  `message` TEXT NOT NULL,
  `sender` VARCHAR(50) NOT NULL,
  `message_type` VARCHAR(50) DEFAULT 'text',
  `intent` VARCHAR(255) NULL,
  `confidence` FLOAT NULL,
  `source` VARCHAR(50) NULL,
  `metadata` JSON NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_session_id` (`session_id`),
  INDEX `idx_sender` (`sender`),
  INDEX `idx_created_at` (`created_at`),
  INDEX `idx_session_sender` (`session_id`, `sender`),
  INDEX `idx_session_created` (`session_id`, `created_at`),
  FOREIGN KEY (`session_id`) REFERENCES `chat_sessions`(`session_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
