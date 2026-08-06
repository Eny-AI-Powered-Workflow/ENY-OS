#!/usr/bin/env python3
import json
import base64
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create database engine
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def decode_jwt_part(part):
    """Decode a base64url-encoded JWT part."""
    # Add padding if needed
    part = part.replace('-', '+').replace('_', '/')
    padding = 4 - len(part) % 4
    if padding != 4:
        part += '=' * padding
    return base64.b64decode(part)

def get_user_id_from_token(token):
    """Extract the user ID (sub) from a JWT token without verification."""
    try:
        header_b64, payload_b64, sig_b64 = token.split('.')
        payload_json = decode_jwt_part(payload_b64)
        payload = json.loads(payload_json)
        return payload.get('sub')
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None

def check_user_role(user_id):
    db = SessionLocal()
    try:
        # Check if the user has the CEO role
        result = db.execute(
            text("""
                SELECT r.name
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id
            """),
            {"user_id": user_id}
        )
        roles = result.fetchall()
        if not roles:
            print(f"No roles found for user {user_id}")
            return False
        role_names = [r[0] for r in roles]
        print(f"User {user_id} has roles: {role_names}")
        return 'ceo' in role_names
    finally:
        db.close()

def main():
    # Use the token from the user's latest output
    token = "eyJhbGciOiJFUzI1NiIsImtpZCI6Ijg5NDljYWNlLThkYmYtNGU3YS04NmM2LWE3ZDA5ODY3MDc2ZiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2NweXRwcmV3bndlZml1ZmVnZ3F0LnN1cGFiYXNlLmNvL2F1dG8vMjEiLCJzdWIiOiJhMmQzYWQxOC1lOTFkLTQ2MjItODU5My0xMDYyMDY1MGZlZDQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzg1OTM5NjQ5LCJpYXQiOjE3ODU5MzYwNDksImVtYWlsIjoiY2VvQHRlc3QuZW55LmRldiIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWUsInJvbGVzIjpbImNlbyJdLCJyb2xlIjoiYXV0aGVudGljYWVkIiwiYWFsIjoiYWFsMSIsImFtcCI6W3sidGVybSI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzg1OTM2MDQ4fV0sInNlc3Npb25faWQiOiIyOWQ0YmJlLTRiZDYtNDM2Zi1iYmJhLTI5ZmQxMjJlNzE0MiIsImlzX2Fub25tb3VzIjpmYWxzZX0.Csk-8MOjnUyQZ2j0IrQSfxxeet0K0IRjtWweZ6CL-numlKOBmoQYU1M-Hyj-1Z8hot8fseH3FsTylHx1HM9dZA"
    user_id = get_user_id_from_token(token)
    if not user_id:
        print("Failed to extract user ID from token")
        return
    print(f"User ID from token: {user_id}")
    has_ceo_role = check_user_role(user_id)
    if has_ceo_role:
        print("SUCCESS: User has the CEO role.")
    else:
        print("ERROR: User does NOT have the CEO role.")

if __name__ == "__main__":
    main()