-- Store structured resume optimization payloads so selected suggestions can be applied.
-- Run this once on an existing smart_resume_platform database.

ALTER TABLE `opt`
  ADD COLUMN `result_json` TEXT NULL COMMENT '结构化优化结果 JSON，用于采纳写回简历' AFTER `content`;
