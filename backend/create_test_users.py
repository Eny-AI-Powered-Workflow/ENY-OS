import os
import requests
import json

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

users = [
    {
        "email": "ceo@test.eny.dev",
        "password": "CEOAdmin123!",
        "email_confirm": True,
        "user_metadata": {"roles": ["ceo"]},
    },
    {
        "email": "enrollment@test.eny.dev",
        "password": "Enroll123!",
        "email_confirm": True,
        "user_metadata": {"roles": ["enrollment"]},
    },
    {
        "email": "programs_manager@test.eny.dev",
        "password": "Program123!",
        "email_confirm": True,
        "user_metadata": {"roles": ["programs_manager"]},
    },
    {
        "email": "customer_service@test.eny.dev",
        "password": "Support123!",
        "email_confirm": True,
        "user_metadata": {"roles": ["customer_success"]},
    },
    {
        "email": "business_support@test.eny.dev",
        "password": "Business123!",
        "email_confirm": True,
        "user_metadata": {"roles": ["business_support"]},
    },
    {
        "email": "executive_assistant@test.eny.dev",
        "password": "Assistant123!",
        "email_confirm": True,
        "user_metadata": {"roles": ["executive_assistant"]},
    },
    {
        "email": "developer@test.eny.dev",
        "password": "Dev123!@#",
        "email_confirm": True,
        "user_metadata": {"roles": ["developer"]},
    },
]

for user in users:
    print(f"Creating user {user['email']}...")
    response = requests.post(url, headers=headers, data=json.dumps(user))
    if response.status_code == 200:
        print(f"  Success: {response.json()}")
    else:
        print(f"  Error: {response.status_code} - {response.text}")