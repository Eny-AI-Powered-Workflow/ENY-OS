#!/usr/bin/env python3
import os
import json

def check_dashboard_modules():
    dashboard_path = "/home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard"

    if not os.path.exists(dashboard_path):
        print("Dashboard path does not exist!")
        return

    print("=== DASHBOARD MODULES ===")
    print(f"Checking: {dashboard_path}")

    # Check for module directories and files
    modules = []
    for item in os.listdir(dashboard_path):
        item_path = os.path.join(dashboard_path, item)
        if os.path.isdir(item_path):
            # Check if it has a page.tsx or similar
            page_tsx = os.path.join(item_path, "page.tsx")
            page_ts = os.path.join(item_path, "page.ts")
            route_tsx = os.path.join(item_path, "route.tsx")
            route_ts = os.path.join(item_path, "route.ts")

            if os.path.exists(page_tsx) or os.path.exists(page_ts) or os.path.exists(route_tsx) or os.path.exists(route_ts):
                modules.append(item)
                print(f"  [MODULE] {item}")
            else:
                print(f"  [DIR]    {item} (no page/route file)")
        elif item.endswith(('.tsx', '.ts')):
            print(f"  [FILE]   {item}")

    print(f"\nFound {len(modules)} dashboard modules: {modules}")

    # Also check the permissions.ts MODULES array
    permissions_path = "/home/obed/Documents/Eny_consulting/Eny_consulting/frontend/lib/permissions.ts"
    if os.path.exists(permissions_path):
        print("\n=== PERMISSIONS.TS MODULES ARRAY ===")
        with open(permissions_path, 'r') as f:
            content = f.read()
            # Extract the MODULES array
            start = content.find('export const MODULES: Module[] = [')
            if start != -1:
                end = content.find(']', start)
                if end != -1:
                    modules_content = content[start:end+1]
                    print(modules_content)
                else:
                    print("Could not find end of MODULES array")
            else:
                print("Could not find MODULES array definition")

if __name__ == "__main__":
    check_dashboard_modules()