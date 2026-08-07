#!/usr/bin/env python3
import os

def check_ceo_endpoints():
    endpoints_path = "/home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints"
    ceo_file = os.path.join(endpoints_path, "ceo.py")

    if os.path.exists(ceo_file):
        print("CEO endpoints file exists:")
        with open(ceo_file, 'r') as f:
            content = f.read()
            print(content)
    else:
        print("CEO endpoints file does not exist - needs to be created")

    # Also check if there are any ceo-related endpoints in other files
    print("\nChecking for ceo-related endpoints in existing files:")
    for f in os.listdir(endpoints_path):
        if f.endswith(".py") and f != "__init__.py":
            filepath = os.path.join(endpoints_path, f)
            with open(filepath, 'r') as fp:
                content = fp.read()
                if 'ceo' in content.lower():
                    print(f"  Found in {f}:")
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'ceo' in line.lower():
                            print(f"    Line {i+1}: {line.strip()}")

if __name__ == "__main__":
    check_ceo_endpoints()