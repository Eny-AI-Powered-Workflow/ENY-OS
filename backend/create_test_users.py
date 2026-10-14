import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment")
    exit(1)

# The admin API endpoint
url = f"{SUPABASE_URL}/auth/v1/admin/users"

headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

roles_response = requests.get(
    f"{SUPABASE_URL}/rest/v1/roles",
    params={"select": "id,name"},
    headers=headers,
    timeout=20,
)
if not roles_response.ok:
    print(f"Unable to load RBAC roles: {roles_response.status_code} - {roles_response.text}")
    exit(1)
role_ids = {role["name"]: role["id"] for role in roles_response.json()}

users = [
    {
        "email": "ceo@test.eny.dev",
        "password": "CEOAdmin123!",
        "email_confirm": True,
        "role": "ceo",
    },
    {
        "email": "enrollment@test.eny.dev",
        "password": "Enroll123!",
        "email_confirm": True,
        "role": "enrollment",
    },
    {
        "email": "programs_manager@test.eny.dev",
        "password": "Program123!",
        "email_confirm": True,
        "role": "programs_manager",
    },
    {
        "email": "customer_service@test.eny.dev",
        "password": "Support123!",
        "email_confirm": True,
        "role": "customer_success",
    },
    {
        "email": "business_support@test.eny.dev",
        "password": "Business123!",
        "email_confirm": True,
        "role": "business_support",
    },
    {
        "email": "executive_assistant@test.eny.dev",
        "password": "Assistant123!",
        "email_confirm": True,
        "role": "executive_assistant",
    },
    {
        "email": "developer@test.eny.dev",
        "password": "Dev123!@#",
        "email_confirm": True,
        "role": "developer",
    },
]

for user in users:
    print(f"Creating user {user['email']}...")
    role_name = user.pop("role")
    role_id = role_ids.get(role_name)
    if not role_id:
        print(f"  Error: RBAC role '{role_name}' does not exist")
        continue

    response = requests.post(url, headers=headers, json=user, timeout=20)
    if response.status_code in (200, 201):
        auth_user_id = response.json().get("id")
        if not auth_user_id:
            print("  Error: Supabase Auth returned no user id")
            continue
        assignment_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/user_roles",
            headers={**headers, "Prefer": "return=minimal"},
            json={"user_id": auth_user_id, "role_id": role_id},
            timeout=20,
        )
        if assignment_response.ok:
            print(f"  Created and assigned role '{role_name}'")
        else:
            print(
                "  Auth account created, but role assignment failed: "
                f"{assignment_response.status_code} - {assignment_response.text}"
            )
    else:
        print(f"  Error: {response.status_code} - {response.text}")