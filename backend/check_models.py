#!/usr/bin/env python3
import os

def check_models():
    models_path = "/home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models"
    if not os.path.exists(models_path):
        print("Models path not found")
        return

    print("=== MODELS FILES ===")
    for f in os.listdir(models_path):
        if f.endswith(".py"):
            print(f"  - {f}")

    # Check specific models
    print("\n=== MODEL CONTENT SNIPPETS ===")
    for model_name in ["user_role", "role", "permission", "role_permission", "audit_log", "agent_log"]:
        file_path = os.path.join(models_path, f"{model_name}.py")
        if os.path.exists(file_path):
            print(f"\n--- {model_name}.py ---")
            with open(file_path, 'r') as f:
                content = f.read()
                # Show first 30 lines
                lines = content.split('\n')[:30]
                for line in lines:
                    print(line)
        else:
            print(f"\n--- {model_name}.py --- NOT FOUND")

if __name__ == "__main__":
    check_models()