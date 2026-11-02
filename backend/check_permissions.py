#!/usr/bin/env python3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create database engine
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_permissions():
    db = SessionLocal()
    try:
        # Check if the CEO role exists
        result = db.execute(text("SELECT id FROM roles WHERE name = 'ceo'"))
        ceo_role = result.fetchone()
        if not ceo_role:
            print("CEO role not found")
            return
        ceo_role_id = ceo_role[0]
        print(f"CEO role ID: {ceo_role_id}")

        # Check if the leads:read permission exists
        result = db.execute(text("SELECT id FROM permissions WHERE scope = 'leads:read'"))
        leads_read_perm = result.fetchone()
        if not leads_read_perm:
            print("leads:read permission not found")
            return
        leads_read_perm_id = leads_read_perm[0]
        print(f"leads:read permission ID: {leads_read_perm_id}")

        # Check if the CEO role has the leads:read permission
        result = db.execute(
            text("SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"),
            {"role_id": ceo_role_id, "perm_id": leads_read_perm_id}
        )
        has_permission = result.fetchone() is not None
        print(f"CEO role has leads:read permission: {has_permission}")

        if has_permission:
            print("SUCCESS: CEO role has the required permission.")
        else:
            print("ERROR: CEO role does NOT have the required permission.")

    finally:
        db.close()

if __name__ == "__main__":
    check_permissions()