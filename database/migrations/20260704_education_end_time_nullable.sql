-- Allow ongoing education entries such as "2023-09 至今" to be stored faithfully.
-- Run this once on an existing smart_resume_platform database.

ALTER TABLE `education_info`
  MODIFY COLUMN `end_time` DATE NULL COMMENT '毕业时间，至今可为空';
