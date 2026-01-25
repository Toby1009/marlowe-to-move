import subprocess
import json
import sys
import os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
DEPLOYMENT_FILE = os.path.join(ROOT_DIR, "deployments", "deployment.json")

def run_command(command, cwd=None):
    print(f"Running: {command} in {cwd or 'current dir'}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print("STDERR:", e.stderr)
        sys.exit(1)

def main():
    print("--- Starting Deployment ---")
    
    CONTRACT_DIR = os.path.join(ROOT_DIR, "contract")
    
    # 2. Publish
    print("Publishing package to Sui...")
    # Must run in CONTRACT_DIR where Move.toml is
    json_output = run_command("sui client publish --gas-budget 100000000 --json --skip-dependency-verification", cwd=CONTRACT_DIR)
    
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        print("Failed to decode JSON output from sui client publish")
        print(json_output)
        sys.exit(1)

    # 3. Parse Output
    package_id = None
    contract_id = None
    upgrade_cap_id = None
    
    if "objectChanges" in data:
        for change in data["objectChanges"]:
            if change["type"] == "published":
                package_id = change["packageId"]
            elif change["type"] == "created":
                obj_type = change["objectType"]
                # Look for Contract
                if "::Contract" in obj_type:
                    contract_id = change["objectId"]
                # Look for UpgradeCap
                if "::package::UpgradeCap" in obj_type:
                     upgrade_cap_id = change["objectId"]

    if not package_id:
        print("❌ Failed to find Package ID in output.")
        sys.exit(1)

    print(f"✅ Deployment Successful!")
    print(f"Package ID: {package_id}")
    print(f"Contract ID: {contract_id}")
    print(f"Upgrade Cap ID: {upgrade_cap_id}")

    # 4. Save to deployment.json
    deployment_info = {
        "package_id": package_id,
        "contract_id": contract_id,
        "upgrade_cap_id": upgrade_cap_id,
        "network": "testnet", # Assumption, or parse from sui client active-env
        "digest": data.get("digest", "")
    }

    os.makedirs(os.path.dirname(DEPLOYMENT_FILE), exist_ok=True)
    with open(DEPLOYMENT_FILE, "w") as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"Artifacts saved to {DEPLOYMENT_FILE}")

if __name__ == "__main__":
    main()
