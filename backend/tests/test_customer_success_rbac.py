# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_customer_success_rbac.py
import re
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def _explicit_scopes_for_role(role_name: str) -> set[str]:
    scopes: set[str] = set()
    role_pattern = re.compile(
        rf"\br\.name\s*=\s*'{re.escape(role_name)}'"
        rf"|\br\.name\s+in\s*\([^)]*'{re.escape(role_name)}'",
        re.IGNORECASE,
    )

    for migration in MIGRATIONS_DIR.glob("*.sql"):
        sql = migration.read_text(encoding="utf-8")
        statements = re.finditer(
            r"insert\s+into\s+role_permissions\b.*?;",
            sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for statement_match in statements:
            statement = statement_match.group(0)
            if not role_pattern.search(statement):
                continue
            scopes.update(re.findall(r"\bp\.scope\s*=\s*'([^']+)'", statement, re.IGNORECASE))
            for scope_list in re.findall(
                r"\bp\.scope\s+in\s*\(([^)]*)\)", statement, re.IGNORECASE | re.DOTALL
            ):
                scopes.update(re.findall(r"'([^']+)'", scope_list))

    return scopes


def test_customer_success_scopes_have_explicit_ceo_grants():
    customer_success_scopes = _explicit_scopes_for_role("customer_success")
    ceo_scopes = _explicit_scopes_for_role("ceo")

    assert {"students:read", "students:write"} <= customer_success_scopes
    assert customer_success_scopes <= ceo_scopes