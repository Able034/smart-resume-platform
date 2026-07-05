import os
import sys
from pathlib import Path

from sqlalchemy import text


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.pop("SSLKEYLOGFILE", None)

from app.db.session import engine  # noqa: E402


def column_exists(table_name: str, column_name: str) -> bool:
    statement = text(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
          AND COLUMN_NAME = :column_name
        """
    )
    with engine.connect() as conn:
        return bool(
            conn.scalar(
                statement,
                {"table_name": table_name, "column_name": column_name},
            )
        )


def table_exists(table_name: str) -> bool:
    statement = text(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
        """
    )
    with engine.connect() as conn:
        return bool(conn.scalar(statement, {"table_name": table_name}))


def column_is_nullable(table_name: str, column_name: str) -> bool:
    statement = text(
        """
        SELECT IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
          AND COLUMN_NAME = :column_name
        """
    )
    with engine.connect() as conn:
        return conn.scalar(
            statement,
            {"table_name": table_name, "column_name": column_name},
        ) == "YES"


def column_data_type(table_name: str, column_name: str) -> str | None:
    statement = text(
        """
        SELECT DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
          AND COLUMN_NAME = :column_name
        """
    )
    with engine.connect() as conn:
        value = conn.scalar(
            statement,
            {"table_name": table_name, "column_name": column_name},
        )
        return str(value).lower() if value else None


def apply_patches() -> list[str]:
    applied: list[str] = []
    with engine.begin() as conn:
        if not table_exists("system_log"):
            conn.execute(
                text(
                    """
                    CREATE TABLE `system_log` (
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
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统操作日志表'
                    """
                )
            )
            applied.append("system_log table")

        if not column_exists("opt", "result_json"):
            conn.execute(
                text(
                    """
                    ALTER TABLE `opt`
                    ADD COLUMN `result_json` TEXT NULL
                    COMMENT '结构化优化结果 JSON，用于采纳写回简历'
                    AFTER `content`
                    """
                )
            )
            applied.append("opt.result_json")

        if not column_is_nullable("education_info", "end_time"):
            conn.execute(
                text(
                    """
                    ALTER TABLE `education_info`
                    MODIFY COLUMN `end_time` DATE NULL
                    COMMENT '毕业时间，至今可为空'
                    """
                )
            )
            applied.append("education_info.end_time nullable")

        if column_data_type("job", "job_url") != "text":
            conn.execute(
                text(
                    """
                    ALTER TABLE `job`
                    MODIFY COLUMN `job_url` TEXT NOT NULL
                    COMMENT '岗位 URL'
                    """
                )
            )
            applied.append("job.job_url text")
    return applied


def main() -> None:
    applied = apply_patches()
    if applied:
        print("Applied schema patches:")
        for item in applied:
            print(f"- {item}")
    else:
        print("Schema is already up to date.")


if __name__ == "__main__":
    main()
