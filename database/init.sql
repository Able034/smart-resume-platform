-- Smart Resume Platform database initialization script
-- Based on docs/数据库设计 (2).md
-- Target database: MySQL / InnoDB

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS smart_resume_platform
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE smart_resume_platform;

DROP TABLE IF EXISTS `opt`;
DROP TABLE IF EXISTS `job`;
DROP TABLE IF EXISTS `award_info`;
DROP TABLE IF EXISTS `intern_info`;
DROP TABLE IF EXISTS `project_info`;
DROP TABLE IF EXISTS `education_info`;
DROP TABLE IF EXISTS `resume`;
DROP TABLE IF EXISTS `resume_template`;
DROP TABLE IF EXISTS `user_account`;

CREATE TABLE `user_account` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户 ID',
  `account` VARCHAR(50) NOT NULL COMMENT '登录账号',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '加密后的密码',
  `email` VARCHAR(100) NULL COMMENT '邮箱',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE、DISABLED',
  `role` VARCHAR(20) NOT NULL DEFAULT 'USER' COMMENT 'USER、ADMIN',
  `register_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  `last_login_time` DATETIME NULL COMMENT '最近登录时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_account_account` (`account`),
  UNIQUE KEY `uk_user_account_email` (`email`),
  KEY `idx_user_account_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户账户表';

CREATE TABLE `resume_template` (
  `resume_template_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '简历模板 ID',
  `template_name` VARCHAR(100) NOT NULL COMMENT '模板名称',
  `latex` VARCHAR(255) NOT NULL COMMENT 'LaTeX 模板文件路径，相对项目路径',
  `preview_url` VARCHAR(255) NULL COMMENT '模板预览图地址',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE、DISABLED',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`resume_template_id`),
  KEY `idx_resume_template_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统预置 LaTeX 简历模板表';

CREATE TABLE `resume` (
  `resume_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '简历 ID',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '关联用户 ID',
  `resume_template_id` BIGINT UNSIGNED NULL COMMENT '关联用户选择的 LaTeX 模板 ID',
  `title` VARCHAR(100) NOT NULL COMMENT '简历标题',
  `name` VARCHAR(100) NULL COMMENT '候选人姓名',
  `age` INT NULL COMMENT '年龄',
  `email` VARCHAR(100) NULL COMMENT '简历邮箱',
  `phone` VARCHAR(50) NULL COMMENT '联系电话',
  `expected_salary` VARCHAR(100) NULL COMMENT '期望薪资',
  `expected_position` VARCHAR(150) NULL COMMENT '期望岗位',
  `skill_name` TEXT NOT NULL COMMENT '简历里的技能名称集合',
  `personal_context` TEXT NOT NULL COMMENT '简历里的个人介绍',
  `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT' COMMENT 'DRAFT、SAVED、ARCHIVED',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` DATETIME NULL COMMENT '软删除时间',
  PRIMARY KEY (`resume_id`),
  KEY `idx_resume_user_id` (`user_id`),
  KEY `idx_resume_template_id` (`resume_template_id`),
  KEY `idx_resume_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历表';

CREATE TABLE `education_info` (
  `education_info_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '教育背景 ID',
  `resume_id` BIGINT UNSIGNED NOT NULL COMMENT '关联简历 ID',
  `university` VARCHAR(100) NOT NULL COMMENT '大学名字',
  `major` VARCHAR(100) NOT NULL COMMENT '专业',
  `degree` VARCHAR(30) NOT NULL COMMENT '学历',
  `start_time` DATE NOT NULL COMMENT '就读开始时间',
  `end_time` DATE NULL COMMENT '毕业时间，至今可为空',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`education_info_id`),
  KEY `idx_education_info_resume_id` (`resume_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历里的教育背景表';

CREATE TABLE `project_info` (
  `project_info_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '项目经历 ID',
  `resume_id` BIGINT UNSIGNED NOT NULL COMMENT '关联简历 ID',
  `project_name` VARCHAR(100) NOT NULL COMMENT '项目名称',
  `role` VARCHAR(100) NULL COMMENT '担任角色',
  `introduction` TEXT NULL COMMENT '项目简介',
  `content` TEXT NOT NULL COMMENT '项目经历内容',
  `start_time` DATE NULL COMMENT '项目开始时间',
  `end_time` DATE NULL COMMENT '项目结束时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`project_info_id`),
  KEY `idx_project_info_resume_id` (`resume_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历里的项目经历表';

CREATE TABLE `intern_info` (
  `intern_info_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '实习经历 ID',
  `resume_id` BIGINT UNSIGNED NOT NULL COMMENT '关联简历 ID',
  `company` VARCHAR(100) NOT NULL COMMENT '公司名称',
  `role` VARCHAR(100) NULL COMMENT '担任角色',
  `content` TEXT NOT NULL COMMENT '实习经历内容',
  `start_time` DATE NULL COMMENT '实习开始时间',
  `end_time` DATE NULL COMMENT '实习结束时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`intern_info_id`),
  KEY `idx_intern_info_resume_id` (`resume_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历里的实习经历表';

CREATE TABLE `award_info` (
  `award_info_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '获奖 ID',
  `resume_id` BIGINT UNSIGNED NOT NULL COMMENT '关联简历 ID',
  `name` VARCHAR(150) NOT NULL COMMENT '奖项名称',
  `award_time` DATE NULL COMMENT '获奖时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`award_info_id`),
  KEY `idx_award_info_resume_id` (`resume_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历里的获奖经历表';

CREATE TABLE `job` (
  `job_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '岗位 ID',
  `resume_id` BIGINT UNSIGNED NOT NULL COMMENT '关联简历 ID',
  `job_url` TEXT NOT NULL COMMENT '岗位 URL',
  `job_name` VARCHAR(150) NULL COMMENT '岗位名称',
  `company` VARCHAR(150) NULL COMMENT '公司名称',
  `content` TEXT NOT NULL COMMENT '抓取的岗位正文、岗位要求、匹配度、置信来源等分析内容',
  `status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING、PARSED、FAILED',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`job_id`),
  KEY `idx_job_resume_id` (`resume_id`),
  KEY `idx_job_status` (`status`),
  KEY `idx_job_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位解析与匹配分析表';

CREATE TABLE `opt` (
  `opt_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '优化 ID',
  `resume_id` BIGINT UNSIGNED NOT NULL COMMENT '关联简历 ID',
  `job_id` BIGINT UNSIGNED NULL COMMENT '关联岗位 ID',
  `content` TEXT NOT NULL COMMENT '优化内容',
  `result_json` TEXT NULL COMMENT '结构化优化结果 JSON，用于采纳写回简历',
  `score` DECIMAL(5,2) NULL COMMENT '简历评分或岗位匹配度评分',
  `status` VARCHAR(20) NOT NULL DEFAULT 'NEW' COMMENT 'NEW、SAVED、USED',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`opt_id`),
  KEY `idx_opt_resume_id` (`resume_id`),
  KEY `idx_opt_job_id` (`job_id`),
  KEY `idx_opt_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历优化建议表';

INSERT INTO `resume_template`
  (`resume_template_id`, `template_name`, `latex`, `preview_url`, `status`)
VALUES
  (1, '中文经典模板 1', 'Latex/1/resume/resume-zh_CN.tex', NULL, 'ACTIVE'),
  (2, '经典单栏模板', 'templates/resume/classic.tex', NULL, 'ACTIVE'),
  (3, '技术简历模板', 'templates/resume/tech.tex', NULL, 'ACTIVE'),
  (4, '简洁中文模板', 'templates/resume/simple-cn.tex', NULL, 'ACTIVE');
