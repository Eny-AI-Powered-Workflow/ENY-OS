# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/check_enrollment_schema.py
"""Verify the Enrollment operations tables and columns in the configured database."""
from sqlalchemy import inspect

from app.db.session import engine

REQUIRED_COLUMNS = {
    "batch_execution_results": {
        "approval_id", "contact_id", "status", "retry_count", "queue_status",
        "assigned_user_id", "follow_up_status", "follow_up_at",
    },
    "batch_retries": {
        "result_id", "attempt_number", "status", "next_attempt_at",
    },
    "enrollment_audit_events": {
        "user_id", "result_id", "event_type", "details",
    },
}


def main() -> int:
    inspector = inspect(engine)
    missing_tables = []
    missing_columns = []
    for table, columns in REQUIRED_COLUMNS.items():
        if not inspector.has_table(table):
            missing_tables.append(table)
            continue
        actual = {column["name"] for column in inspector.get_columns(table)}
        missing_columns.extend(f"{table}.{column}" for column in sorted(columns - actual))

    if missing_tables or missing_columns:
        print("Enrollment schema is incomplete")
        for table in missing_tables:
            print(f"missing table: {table}")
        for column in missing_columns:
            print(f"missing column: {column}")
        return 1

    print("Enrollment schema is ready: batch results, retries, and audit events are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
