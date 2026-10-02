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

    for migration in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
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

        deletions = re.finditer(
            r"delete\s+from\s+role_permissions\b.*?;",
            sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for deletion_match in deletions:
            statement = deletion_match.group(0)
            if not role_pattern.search(statement):
                continue
            revoked_scopes = set(re.findall(r"\bp\.scope\s*=\s*'([^']+)'", statement, re.IGNORECASE))
            for scope_list in re.findall(
                r"\bp\.scope\s+in\s*\(([^)]*)\)", statement, re.IGNORECASE | re.DOTALL
            ):
                revoked_scopes.update(re.findall(r"'([^']+)'", scope_list))
            scopes.difference_update(revoked_scopes)

    return scopes


def _business_support_scopes() -> set[str]:
    scopes: set[str] = set()
    for migration in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        sql = migration.read_text(encoding="utf-8")
        permission_inserts = re.finditer(
            r"insert\s+into\s+permissions\b.*?;",
            sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for statement_match in permission_inserts:
            scopes.update(
                scope
                for scope in re.findall(r"'([^']+)'", statement_match.group(0))
                if scope.startswith("business_support:")
            )
    return scopes


def test_customer_success_scopes_have_explicit_ceo_grants():
    customer_success_scopes = _explicit_scopes_for_role("customer_success")
    ceo_scopes = _explicit_scopes_for_role("ceo")

    assert "students:read" in customer_success_scopes
    assert "students:write" not in customer_success_scopes
    assert {"payments:kajabi:read", "payments:paystack:read"} <= customer_success_scopes
    assert customer_success_scopes <= ceo_scopes


def test_customer_success_has_no_payment_verification_or_access_grant_scope():
    customer_success_scopes = _explicit_scopes_for_role("customer_success")

    assert "payments:verify" not in customer_success_scopes
    assert "students:course_access:grant" not in customer_success_scopes


def test_programs_manager_has_student_read_access_for_oversight():
    programs_manager_scopes = _explicit_scopes_for_role("programs_manager")

    assert "students:read" in programs_manager_scopes


def test_payment_and_lifecycle_scopes_follow_the_phase_three_matrix():
    customer_success_scopes = _explicit_scopes_for_role("customer_success")
    programs_manager_scopes = _explicit_scopes_for_role("programs_manager")
    business_support_scopes = _explicit_scopes_for_role("business_support")
    ceo_scopes = _explicit_scopes_for_role("ceo")
    phase_three_scopes = {
        "payments:kajabi:read",
        "payments:paystack:read",
        "payments:verify",
        "students:attendance:read",
        "students:attendance:write",
        "students:assignments:read",
        "students:intervention:review",
        "students:intervention:approve",
        "students:course_access:request",
        "students:course_access:grant",
        "students:course_access:approve",
    }

    assert phase_three_scopes <= ceo_scopes
    assert {"payments:kajabi:read", "payments:paystack:read"} <= programs_manager_scopes
    assert {"payments:kajabi:read", "payments:paystack:read", "payments:verify"} <= business_support_scopes
    assert {"students:intervention:approve", "students:course_access:approve"} <= programs_manager_scopes
    assert {"payments:kajabi:read", "payments:paystack:read"} <= customer_success_scopes
    assert "payments:verify" not in customer_success_scopes
    assert "students:course_access:grant" not in customer_success_scopes


def test_business_support_scopes_are_explicitly_granted_to_business_support_and_ceo():
    business_support_scopes = _business_support_scopes()

    assert "business_support:dashboard:read" in business_support_scopes
    assert business_support_scopes <= _explicit_scopes_for_role("business_support")
    assert business_support_scopes <= _explicit_scopes_for_role("ceo")


def test_signaturely_contract_read_is_limited_to_business_support_ceo_and_programs_manager():
    business_support_scopes = _explicit_scopes_for_role("business_support")
    ceo_scopes = _explicit_scopes_for_role("ceo")
    programs_manager_scopes = _explicit_scopes_for_role("programs_manager")
    customer_success_scopes = _explicit_scopes_for_role("customer_success")

    assert "business_support:contracts:read" in business_support_scopes
    assert "business_support:contracts:read" in ceo_scopes
    assert "business_support:contracts:read" in programs_manager_scopes
    assert "business_support:contracts:read" not in customer_success_scopes
    assert "business_support:contracts:write" not in business_support_scopes
    assert "business_support:contracts:write" not in programs_manager_scopes