-- Admin account setup.
-- Usage:
-- 1. Register a normal account from the frontend, for example account = 'admin'.
-- 2. Replace 'admin' below with that account and execute this SQL.

UPDATE `user_account`
SET `role` = 'ADMIN',
    `status` = 'ACTIVE'
WHERE `account` = 'admin';
