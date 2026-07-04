-- Add fields required by PDF resume parsing.
-- Run this once on an existing smart_resume_platform database.

ALTER TABLE `resume`
  ADD COLUMN `name` VARCHAR(100) NULL COMMENT '候选人姓名' AFTER `title`,
  ADD COLUMN `age` INT NULL COMMENT '年龄' AFTER `name`,
  ADD COLUMN `email` VARCHAR(100) NULL COMMENT '简历邮箱' AFTER `age`,
  ADD COLUMN `phone` VARCHAR(50) NULL COMMENT '联系电话' AFTER `email`,
  ADD COLUMN `expected_salary` VARCHAR(100) NULL COMMENT '期望薪资' AFTER `phone`,
  ADD COLUMN `expected_position` VARCHAR(150) NULL COMMENT '期望岗位' AFTER `expected_salary`;

ALTER TABLE `project_info`
  MODIFY COLUMN `role` VARCHAR(100) NULL COMMENT '担任角色',
  MODIFY COLUMN `introduction` TEXT NULL COMMENT '项目简介',
  MODIFY COLUMN `start_time` DATE NULL COMMENT '项目开始时间',
  MODIFY COLUMN `end_time` DATE NULL COMMENT '项目结束时间';

ALTER TABLE `intern_info`
  MODIFY COLUMN `role` VARCHAR(100) NULL COMMENT '担任角色',
  MODIFY COLUMN `start_time` DATE NULL COMMENT '实习开始时间',
  MODIFY COLUMN `end_time` DATE NULL COMMENT '实习结束时间';

ALTER TABLE `award_info`
  MODIFY COLUMN `award_time` DATE NULL COMMENT '获奖时间';
