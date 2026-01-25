import json
from parser import parse_contract
from fsm_model import parse_contract_to_infos, ChoiceStageInfo
from move_generator import generate_test_module

def main():
    json_filename = "complex_contract.json"
    with open(json_filename, "r") as f:
        json_data = json.load(f)
    contract_ast = parse_contract(json_data)
    (infos, _) = parse_contract_to_infos(contract_ast, stage=0)
    
    print("--- Debug Infos ---")
    for k, v in infos.items():
        print(f"Stage {k}: Type={type(v)}")
        if hasattr(v, 'cases'):
            for idx, case in enumerate(v.cases):
                print(f"  Case {idx}: Action Type={type(case.action)}")
                print(f"  Action Dict: {asdict(case.action) if hasattr(case.action, '__dict__') or hasattr(case.action, '__dataclass_fields__') else case.action}")

    
    print("\n--- Test Module Output ---")
    print(generate_test_module(infos))

if __name__ == "__main__":
    main()
