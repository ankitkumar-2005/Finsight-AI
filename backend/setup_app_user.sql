-- Run this script in MySQL Workbench as an administrator after replacing the placeholder.
-- Use the same password in backend/.env as MYSQL_PASSWORD.
CREATE DATABASE IF NOT EXISTS finsight CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS finsight_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'finsight_app'@'127.0.0.1' IDENTIFIED BY 'REPLACE_WITH_A_STRONG_PASSWORD';
ALTER USER 'finsight_app'@'127.0.0.1' IDENTIFIED BY 'REPLACE_WITH_A_STRONG_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE ON finsight.* TO 'finsight_app'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON finsight_test.* TO 'finsight_app'@'127.0.0.1';
