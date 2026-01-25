import json
from parser import parse_contract
from fsm_model import parse_contract_to_infos
from move_generator import generate_module, build_stage_lookup, generate_test_module
from ts_generator import generate_ts_sdk
import os

def main():
    # Path Setup
    SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
    
    json_path = os.path.join(ROOT_DIR, "specs", "swap_ada.json")
    
    print(f"Loading {json_path}")
    with open(json_path, "r") as f:
        json_data = json.load(f)
        
    print("Parsing contract...")
    contract_ast = parse_contract(json_data)
    
    print("Building info map...")
    (infos, _) = parse_contract_to_infos(contract_ast, stage=0)
    print(f"Detected stages: {len(infos)}")
    
    # 4. 建立 Stage Lookup
    print("Building stage lookup...")
    stage_lookup = build_stage_lookup(infos)

    # 5. 生成 Move 代碼
    print("Generating Move code...")
    move_code = generate_module(infos, stage_lookup)
    
    output_path = os.path.join(ROOT_DIR, "contract", "sources", "swap_ada.move")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write(move_code)
        
    print(f"Success! Output written to \n{output_path}")

    # --- NEW: Generate Mock Dollar for Testing ---
    mock_dollar_code = """
module test::mock_dollar {
    use sui::coin;
    struct DOLLAR has drop {}
}
"""
    mock_path = os.path.join(ROOT_DIR, "contract", "sources", "mock_dollar.move")
    with open(mock_path, "w") as f:
        f.write(mock_dollar_code)
    print(f"Mock Token written to {mock_path}")
    # ---------------------------------------------

    # 6. Generate Test Module
    print("Generating Test module...")
    test_code = generate_test_module(infos)
    test_path = os.path.join(ROOT_DIR, "contract", "tests", "contract_tests.move")
    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    
    with open(test_path, "w") as f:
        f.write(test_code)
    print(f"Tests written to {test_path}")

    # 7. Generate TypeScript SDK
    print("Generating TypeScript SDK...")
    # NOTE: ts_generator probably reads deployment.json?
    # We should update ts_generator to accept deployment path or pass dict.
    # For now, ts_generator reads "deployment.json" by default from CWD.
    # We should pass the correct path.
    deployment_path = os.path.join(ROOT_DIR, "deployments", "deployment.json")
    ts_code = generate_ts_sdk(infos, deployment_path=deployment_path)
    
    ts_path = os.path.join(ROOT_DIR, "sdk", "contract_sdk.ts")
    os.makedirs(os.path.dirname(ts_path), exist_ok=True)
    with open(ts_path, "w") as f:
        f.write(ts_code)
    print(f"SDK written to {ts_path}")

if __name__ == "__main__":
    main()
