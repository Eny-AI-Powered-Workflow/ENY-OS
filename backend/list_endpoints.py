#!/usr/bin/env python3
import os

def list_endpoints():
    endpoints_path = "/home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints"
    if not os.path.exists(endpoints_path):
        print("Endpoints path not found")
        return

    print("=== EXISTING ENDPOINTS ===")
    for f in os.listdir(endpoints_path):
        if f.endswith(".py"):
            print(f"  - {f}")

    # Show content of each
    for f in os.listdir(endpoints_path):
        if f.endswith(".py"):
            path = os.path.join(endpoints_path, f)
            print(f"\n--- {f} ---")
            with open(path, 'r') as fp:
                content = fp.read()
                # Look for @router.get, @router.post, etc.
                lines = content.split('\n')
                for line in lines:
                    if '@router.' in line:
                        print(line.strip())

if __name__ == "__main__":
    list_endpoints()