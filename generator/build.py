import json
from parser import parse_contract
from fsm_model import parse_contract_to_infos
from move_generator import generate_module, build_stage_lookup, generate_test_module
from ts_generator import generate_ts_sdk
import os
import sys

def main():
    # Path Setup
    SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
    
    specs_dir = os.path.join(ROOT_DIR, "specs")
    
    # Iterate all specs
    if not os.path.exists(specs_dir):
        print(f"Error: Specs directory not found at {specs_dir}")
        return

    for filename in os.listdir(specs_dir):
        if not filename.endswith(".json") or filename == "test.json":
            continue
            
        module_name = os.path.splitext(filename)[0]
        json_path = os.path.join(specs_dir, filename)
        print(f"\nProcessing {filename} -> Module: {module_name}")
        
        with open(json_path, "r") as f:
            json_data = json.load(f)
            
        print("Parsing contract...")
        try:
            contract_ast = parse_contract(json_data)
        except Exception as e:
            print(f"Skipping {filename}: Parser error {e}")
            continue
        
        print("Building info map...")
        (infos, _) = parse_contract_to_infos(contract_ast, stage=0)
        
        print("Building stage lookup...")
        stage_lookup = build_stage_lookup(infos)

        print("Generating Move code...")
        move_code = generate_module(infos, stage_lookup, module_name=module_name)
        
        output_path = os.path.join(ROOT_DIR, "contract", "sources", f"{module_name}.move")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(move_code)
        print(f"Move code written to {output_path}")

        print("Generating Test module...")
        test_code = generate_test_module(infos, package_name=module_name)
        test_path = os.path.join(ROOT_DIR, "contract", "tests", f"{module_name}_tests.move")
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        with open(test_path, "w") as f:
            f.write(test_code)
        print(f"Tests written to {test_path}")

        print("Generating TypeScript SDK...")
        deployment_path = os.path.join(ROOT_DIR, "deployments", "deployment.json")
        ts_code = generate_ts_sdk(infos, deployment_path=deployment_path, module_name=module_name)
        
        ts_path = os.path.join(ROOT_DIR, "sdk", f"{module_name}_sdk.ts")
        os.makedirs(os.path.dirname(ts_path), exist_ok=True)
        with open(ts_path, "w") as f:
            f.write(ts_code)
        print(f"SDK written to {ts_path}")

if __name__ == "__main__":
    main()
