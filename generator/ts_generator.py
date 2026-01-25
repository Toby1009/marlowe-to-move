import json
from typing import Dict, List, Any
from fsm_model import ChoiceStageInfo, DepositStageInfo, NotifyStageInfo
from move_generator import parse_party_str

def generate_ts_sdk(infos: Dict[str, List[Any]], deployment_path: str = "deployment.json", module_name: str = "generated_marlowe") -> str:
    # 1. Load Deployment Config
    try:
        with open(deployment_path, "r") as f:
            deploy_config = json.load(f)
            package_id = deploy_config.get("package_id", "0x...")
            contract_id = deploy_config.get("contract_id", "0x...")
    except FileNotFoundError:
        package_id = "YOUR_PACKAGE_ID"
        contract_id = "YOUR_CONTRACT_ID"

    # 2. Header & Imports
    ts_code = f"""
import {{ Transaction }} from '@mysten/sui/transactions';
import {{ bcs }} from '@mysten/sui/bcs';

export const PACKAGE_ID = "{package_id}";
export const CONTRACT_ID = "{contract_id}";

export class MarloweContract {{
    packageId: string;
    contractId: string;
    moduleId: string = "{module_name}";

    constructor(packageId: string = PACKAGE_ID, contractId: string = CONTRACT_ID) {{
        this.packageId = packageId;
        this.contractId = contractId;
    }}

    /**
     * Helper to call a Move function
     */
    private moveCall(tx: Transaction, func: string, args: any[], typeArgs: string[] = []) {{
        tx.moveCall({{
            target: `${{this.packageId}}::${{this.moduleId}}::${{func}}`,
            arguments: args,
            typeArguments: typeArgs,
        }});
    }}

    /**
     * Mint a Role NFT (Requires AdminCap)
     */
    mintRole(tx: Transaction, adminCap: string, name: string, recipient: string) {{
        this.moveCall(tx, 'mint_role', [
            tx.object(adminCap),
            tx.object(this.contractId),
            tx.pure(bcs.string().serialize(name)),
            tx.pure(bcs.Address.serialize(recipient))
        ]);
    }}

    /**
     * Withdraw Assets (via Role)
     * @param typeArg The Coin Type (e.g. '0x2::sui::SUI')
     */
    withdraw(tx: Transaction, roleNftId: string, amount: bigint, typeArg: string) {{
        this.moveCall(
            tx, 
            'withdraw_by_role', 
            [
                tx.object(this.contractId),
                tx.object(roleNftId),
                tx.pure(bcs.u64().serialize(amount))
            ],
            [typeArg]
        );
    }}
"""

    # 3. Generate Methods for Each Stage
    # Iterate through all stages in 'infos'
    # We want to sort them by stage/case to be neat, but dict iteration involves keys "choice", "deposit" etc.
    # Let's just iterate logical types.

    # --- Choices ---
    if "choice" in infos:
        for choice in infos["choice"]:
            fn_name = f"choice_stage_{choice.stage}_case_{choice.case_index}"
            ts_method_name = f"choice_Stage{choice.stage}_{choice.case_index}_{choice.choice_name}"
            
            (party_type, party_name) = parse_party_str(choice.by)
            
            # Param generation
            # If Role: need (role_nft_obj)
            # If Address: checks sender (no extra arg)
            
            params_doc = f" * @param choiceVal Value between {choice.bounds[0]['from']} and {choice.bounds[0]['to']}" if choice.bounds else ""
            
            if party_type == "role":
                ts_code += f"""
    /**
     * Stage {choice.stage}: Choice '{choice.choice_name}' by Role '{party_name}'
     {params_doc}
     */
    {ts_method_name}(tx: Transaction, roleNftId: string, choiceVal: number | bigint) {{
        this.moveCall(tx, '{fn_name}', [
            tx.object(this.contractId),
            tx.object(roleNftId),
            tx.pure(bcs.u64().serialize(choiceVal))
        ]);
    }}
"""
            else: # Address
                ts_code += f"""
    /**
     * Stage {choice.stage}: Choice '{choice.choice_name}' by Address {party_name}
     {params_doc}
     */
    {ts_method_name}(tx: Transaction, choiceVal: number | bigint) {{
        this.moveCall(tx, '{fn_name}', [
            tx.object(this.contractId),
            tx.pure(bcs.u64().serialize(choiceVal))
        ]);
    }}
"""

    # --- Deposits ---
    if "deposit" in infos:
        for dep in infos["deposit"]:
            fn_name = f"deposit_stage_{dep.stage}_case_{dep.case_index}"
            ts_method_name = f"deposit_Stage{dep.stage}_{dep.case_index}"
            
            # Param: coin object
            ts_code += f"""
    /**
     * Stage {dep.stage}: Deposit into '{dep.into_account}'
     */
    {ts_method_name}(tx: Transaction, coinObj: string) {{
        this.moveCall(tx, '{fn_name}', [
            tx.object(this.contractId),
            tx.object(coinObj)
        ]);
    }}
"""

    # --- Notify ---
    if "notify" in infos:
        for notif in infos["notify"]:
            fn_name = f"notify_stage_{notif.stage}_case_{notif.case_index}"
            ts_method_name = f"notify_Stage{notif.stage}_{notif.case_index}"
            
            ts_code += f"""
    /**
     * Stage {notif.stage}: Notify
     */
    {ts_method_name}(tx: Transaction) {{
        this.moveCall(tx, '{fn_name}', [
            tx.object(this.contractId)
        ]);
    }}
"""

    # --- Timeouts ---
    # Collect Timeouts map
    timeouts_map = {}
    if "when" in infos:
        for when in infos["when"]:
            if when.timeout:
                timeouts_map[when.stage] = when.timeout
            
            # Generate timeout method
            fn_name = f"timeout_stage_{when.stage}"
            ts_method_name = f"timeout_Stage{when.stage}"
            ts_code += f"""
    /**
     * Stage {when.stage}: Timeout Action (Trigger when time >= {when.timeout})
     */
    {ts_method_name}(tx: Transaction) {{
        this.moveCall(tx, '{fn_name}', [
            tx.object(this.contractId)
        ]);
    }}
"""

    # Inject static TIMEOUTS map at top of class? Or end?
    # Actually TypeScript static property.
    # Let's insert it inside the class definition.
    # We can append it now but it needs to be inside class {}.
    # We are already inside class methods loop.
    # Easier: Just add a method `getTimeout(stage: number)` or public static property?
    # Let's add readonly property `timeouts`.
    
    timeouts_json = json.dumps(timeouts_map)
    ts_code += f"""
    public getTimeouts(): Record<number, number> {{
        return {timeouts_json};
    }}
"""

    # End Class
    ts_code += "\n}\n"
    return ts_code

if __name__ == "__main__":
    # Test stub
    pass
