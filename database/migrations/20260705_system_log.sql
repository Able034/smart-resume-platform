-- Add system operation logs for admin audit views.

CREATE TABLE IF NOT EXISTS `system_log` (
  `log_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '日志 ID',
  `user_id` BIGINT UNSIGNED NULL COMMENT '操作用户 ID',
  `action` VARCHAR(80) NOT NULL COMMENT '操作类型',
  `target_type` VARCHAR(80) NULL COMMENT '操作对象类型',
  `target_id` VARCHAR(80) NULL COMMENT '操作对象 ID',
  `detail` TEXT NULL COMMENT '日志详情',
  `ip` VARCHAR(80) NULL COMMENT '客户端 IP',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`log_id`),
  KEY `idx_system_log_user_id` (`user_id`),
  KEY `idx_system_log_action` (`action`),
  KEY `idx_system_log_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统操作日志表';
