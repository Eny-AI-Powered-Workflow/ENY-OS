#!/usr/bin/env python3
import os

def check_agent_workflow_state():
    print("=== AGENT/WORKFLOW STATE ===")

    # Check agents endpoints
    agents_endpoint_path = "/home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/agents.py"
    if os.path.exists(agents_endpoint_path):
        print("\n[EXISTS] Agents endpoint:", agents_endpoint_path)
        with open(agents_endpoint_path, 'r') as f:
            content = f.read()
            print("Content preview:")
            print(content[:500] + ("..." if len(content) > 500 else ""))
    else:
        print("\n[MISSING] Agents endpoint:", agents_endpoint_path)

    # Check workflows directory
    workflows_path = "/home/obed/Documents/Eny_consulting/Eny_consulting/workflows"
    if os.path.exists(workflows_path):
        print(f"\n[EXISTS] Workflows directory: {workflows_path}")
        workflow_files = []
        for item in os.listdir(workflows_path):
            if item.endswith('.json'):
                workflow_files.append(item)
        print(f"JSON workflow files ({len(workflow_files)}): {workflow_files}")

        # Check README
        readme_path = os.path.join(workflows_path, "README.md")
        if os.path.exists(readme_path):
            print("\nWorkflows README:")
            with open(readme_path, 'r') as f:
                print(f.read())
        else:
            print("\n[MISSING] Workflows README")
    else:
        print(f"\n[MISSING] Workflows directory: {workflows_path}")

    # Check if there's an agent trigger endpoint pattern in router
    router_path = "/home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/router.py"
    if os.path.exists(router_path):
        print(f"\n[EXISTS] API Router: {router_path}")
        with open(router_path, 'r') as f:
            content = f.read()
            if 'agents' in content:
                print("Agents router found in router.py")
            else:
                print("Agents router NOT found in router.py")
    else:
        print(f"\n[MISSING] API Router: {router_path}")

if __name__ == "__main__":
    check_agent_workflow_state()