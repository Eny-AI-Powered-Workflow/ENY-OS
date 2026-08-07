#!/usr/bin/env python3
import os

def check_dashboard_routes():
    dashboard_path = "/home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard"
    modules = ["ceo", "enrollment", "student-success", "marketing", "operations", "writer"]
    print("=== DASHBOARD MODULE ROUTES ===")
    for module in modules:
        module_path = os.path.join(dashboard_path, module)
        if os.path.exists(module_path):
            print(f"  [EXISTS] {module}: {module_path}")
            # Check for page.tsx or page.ts or route.tsx/route.ts
            page_tsx = os.path.join(module_path, "page.tsx")
            page_ts = os.path.join(module_path, "page.ts")
            route_tsx = os.path.join(module_path, "route.tsx")
            route_ts = os.path.join(module_path, "route.ts")
            if os.path.exists(page_tsx):
                print(f"    Has page.tsx")
            elif os.path.exists(page_ts):
                print(f"    Has page.ts")
            elif os.path.exists(route_tsx):
                print(f"    Has route.tsx")
            elif os.path.exists(route_ts):
                print(f"    Has route.ts")
            else:
                print(f"    [MISSING] No page or route file")
        else:
            print(f"  [MISSING] {module}: directory does not exist")

if __name__ == "__main__":
    check_dashboard_routes()