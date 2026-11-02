import asyncio
from app.services.ghl_service import ghl_service

async def main():
    print("Testing GHL service...")
    print(f"Private token set: {bool(ghl_service.private_token)}")
    print(f"Location ID set: {bool(ghl_service.location_id)}")
    contacts = await ghl_service.get_contacts(limit=2)
    print(f"Number of contacts retrieved: {len(contacts)}")
    if contacts:
        print(f"First contact: {contacts[0].get('firstName')} {contacts[0].get('lastName')}")
        print(f"Email: {contacts[0].get('email')}")
        print(f"Tags: {contacts[0].get('tags')}")
    else:
        print("No contacts returned.")

if __name__ == "__main__":
    asyncio.run(main())
