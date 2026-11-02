#!/usr/bin/env python3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create database engine
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_rbac_state():
    db = SessionLocal()
    try:
        print("=== CURRENT RBAC STATE ===")

        # Check roles
        result = db.execute(text("SELECT id, name FROM roles ORDER BY name"))
        roles = result.fetchall()
        print(f"\nRoles ({len(roles)}):")
        for role in roles:
            print(f"  - {role[0]}: {role[1]}")

        # Check permissions
        result = db.execute(text("SELECT id, scope FROM permissions ORDER BY scope"))
        permissions = result.fetchall()
        print(f"\nPermissions ({len(permissions)}):")
        for perm in permissions:
            print(f"  - {perm[0]}: {perm[1]}")

        # Check role-permission mappings
        result = db.execute(text("""
            SELECT r.name as role_name, p.scope as permission_scope
            FROM role_permissions rp
            JOIN roles r ON rp.role_id = r.id
            JOIN permissions p ON rp.permission_id = p.id
            ORDER BY r.name, p.scope
        """))
        mappings = result.fetchall()
        print(f"\nRole-Permission Mappings ({len(mappings)}):")
        for mapping in mappings:
            print(f"  - {mapping[0]} -> {mapping[1]}")

        # Check recent audit logs
        result = db.execute(text("""
            SELECT al.id, al.user_id, al.permission_scope, al.granted, al.created_at
            FROM audit_logs al
            ORDER BY al.created_at DESC
            LIMIT 10
        """))
        audit_logs = result.fetchall()
        print(f"\nRecent Audit Logs ({len(audit_logs)}):")
        for log in audit_logs:
            print(f"  - [{log[4]}] User {log[1]}: {log[2]} -> {'GRANTED' if log[3] else 'DENIED'}")

    finally:
        db.close()

if __name__ == "__main__":
    check_rbac_state()