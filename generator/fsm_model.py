# (FIXED) Removed incorrect import
from dataclasses import dataclass, asdict
import json
from typing import Any, Dict, List, Optional, Tuple

# 確保從 marlowe_types 匯入所有需要的類型
from marlowe_types import (
    # Contract Types
    Contract, Close, Pay, If, When, Let, Assert,
    # Base
    Party, AddressParty, RoleParty,
    Payee, AccountPayee, PartyPayee,
    Token,
    # Cases
    Case, Deposit, Choice, Notify,
    # Values
    Value, AvailableMoney, AddValue, SubValue, MulValue, DivValue,
    NegValue, UseValue, Cond, Constant, # Ensure Constant is imported here
    ChoiceValue, TimeIntervalStart, TimeIntervalEnd,
    # Observations
    Observation, TrueObs, FalseObs,
    AndObs, OrObs, NotObs, ChoseSomething,
    ValueGE, ValueGT, ValueLT, ValueLE, ValueEQ,
    # Helpers
    ChoiceId, Bound
)

# 確保您的 parser.py 檔案位於同一目錄或 Python 路徑中
from parser import parse_contract

# --------------------------
# (NEW) Token Type Mapping Helper
# --------------------------

# Global Token Map configuration
# This can be expanded to include Mainnet addresses.
TOKEN_MAP = {
    ":": "sui::sui::SUI",
    "0x2::sui::SUI:SUI": "sui::sui::SUI", # Explicit
    # Mapping for Swap ADA spec (Mock Dollar)
    "85bb65085bb65085bb65085bb65085bb65085bb65085bb65085bb650:dollar": "test::mock_dollar::DOLLAR",
    # Mocks for ETH/USDC
    "test::mock_eth::ETH:ETH": "test::mock_eth::ETH",
    "test::mock_usdc::USDC:USDC": "test::mock_usdc::USDC"
}

def marlowe_token_to_move_type(token_info: Dict[str, str]) -> str:
    """
    Converts Marlowe Token JSON representation to a Sui Move type string.
    Priority:
    1. Lookup in TOKEN_MAP (Key = "symbol:name")
    2. Pass-through if symbol looks like a Move type (contains "::")
    3. Fallback/Error
    """
    currency_symbol = token_info.get("currency_symbol", "")
    token_name = token_info.get("token_name", "")
    
    # 1. Map Lookup
    map_key = f"{currency_symbol}:{token_name}"
    if map_key in TOKEN_MAP:
        return TOKEN_MAP[map_key]
        
    # 2. Heuristic: If symbol is already a fully qualified Move type
    if "::" in currency_symbol:
         return currency_symbol

    # 3. Fallback / Hardcoded Assumptions
    if not currency_symbol and not token_name:
        return "sui::sui::SUI"

    print(f"Warning: Could not map Marlowe token to Move type: {token_info}")
    return "ERROR_UNKNOWN_TOKEN_TYPE"


# --------------------------
# StageInfo dataclasses (REVISED - Added token_type_str)
# --------------------------
@dataclass
class PayStageInfo:
    stage: int
    from_account: str
    to: str
    token: Dict[str, str]
    amount: Any # Value JSON
    next_stage: int
    token_type_str: str = "sui::sui::SUI" # Default

@dataclass
class DepositStageInfo:
    """Deposit: 發生在 When (stage)，觸發後跳轉到 next_stage"""
    stage: int
    case_index: int
    party: str
    into_account: str
    token: Dict[str, str]
    value: Any
    next_stage: int
    token_type_str: str # (NEW) Full Move type string

@dataclass
class ChoiceStageInfo:
    """Choice: 發生在 When (stage)，觸發後跳轉到 next_stage"""
    stage: int
    case_index: int
    choice_name: str
    by: str
    bounds: List[Dict[str, int]]
    next_stage: int

@dataclass
class NotifyStageInfo:
    """Notify: 發生在 When (stage)，觸發後跳轉到 next_stage"""
    stage: int
    case_index: int
    observation: Any
    next_stage: int

@dataclass
class CloseStageInfo:
    """Close: 終端 stage"""
    stage: int

@dataclass
class IfStageInfo:
    """If: 條件分支，根據條件跳轉到 then_stage 或 else_stage"""
    stage: int
    condition: Any
    then_stage: int
    else_stage: int

@dataclass
class LetStageInfo:
    """Let: 自動執行，下一步總是 stage + 1"""
    stage: int
    name: str
    value: Any

@dataclass
class AssertStageInfo:
    """Assert: 自動執行，下一步總是 stage + 1"""
    stage: int
    observation: Any

@dataclass
class WhenStageInfo:
    """When: 等待區塊。包含 Action 列表和一個 timeout"""
    stage: int
    timeout: Any
    cases_count: int
    timeout_stage: int


# --------------------------
# Helpers: serialise AST nodes to JSON-able primitives
# --------------------------

def party_to_str(p: Party) -> str:
    if isinstance(p, RoleParty):
        return f"Role({p.role_token})"
    if isinstance(p, AddressParty):
        return f"Address({p.address})"
    return str(p)


def payee_to_str(payee: Payee) -> str:
    if isinstance(payee, AccountPayee):
        return f"Account({party_to_str(payee.account)})"
    if isinstance(payee, PartyPayee):
        return f"Party({party_to_str(payee.party)})"
    return str(payee)


def token_to_json(token: Token) -> Dict[str, str]:
    return {
        "currency_symbol": getattr(token, "currency_symbol", ""),
        "token_name": getattr(token, "token_name", "")
    }

def choice_id_to_json(cid: ChoiceId) -> Dict[str, Any]:
    owner_obj: Optional[Party] = getattr(cid, "by", None)
    owner_str = party_to_str(owner_obj) if owner_obj is not None else "unknown"
    return {
        "name": getattr(cid, "name", "unknown"),
        "owner": owner_str
    }

def bound_to_json(b: Bound) -> Dict[str, Any]:
    return {
        "from": getattr(b, "from_value", 0),
        "to": getattr(b, "to_value", 0)
    }

def observation_to_json(obs: Observation) -> Any:
    """遞迴地將 Observation 序列化為 JSON-able dict"""
    if isinstance(obs, TrueObs): return True
    if isinstance(obs, FalseObs): return False
    if isinstance(obs, AndObs): return {"both": observation_to_json(obs.left), "and": observation_to_json(obs.right)}
    if isinstance(obs, OrObs): return {"either": observation_to_json(obs.left), "or": observation_to_json(obs.right)}
    if isinstance(obs, NotObs): return {"not": observation_to_json(obs.obs)}
    if isinstance(obs, ChoseSomething): return {"chose_something_for": choice_id_to_json(obs.choice_id)}
    if isinstance(obs, ValueGE): return {"value": value_to_json(obs.lhs), "ge_than": value_to_json(obs.rhs)}
    if isinstance(obs, ValueGT): return {"value": value_to_json(obs.lhs), "gt": value_to_json(obs.rhs)}
    if isinstance(obs, ValueLT): return {"value": value_to_json(obs.lhs), "lt": value_to_json(obs.rhs)}
    if isinstance(obs, ValueLE): return {"value": value_to_json(obs.lhs), "le_than": value_to_json(obs.rhs)}
    if isinstance(obs, ValueEQ): return {"value": value_to_json(obs.lhs), "equal_to": value_to_json(obs.rhs)}
    raise ValueError(f"Unsupported Observation type: {type(obs)}")


def value_to_json(v: Value) -> Any:
    """遞迴地將 Value 序列化為 JSON-able dict"""
    if isinstance(v, Constant): return v.value
    if isinstance(v, NegValue): return {"negate": value_to_json(v.value)}
    if isinstance(v, AddValue): return {"add": [value_to_json(v.lhs), value_to_json(v.rhs)]}
    if isinstance(v, SubValue): return {"sub": [value_to_json(v.lhs), value_to_json(v.rhs)]}
    if isinstance(v, MulValue): return {"mul": [value_to_json(v.lhs), value_to_json(v.rhs)]}
    if isinstance(v, DivValue): return {"div": [value_to_json(v.lhs), value_to_json(v.rhs)]}
    if isinstance(v, AvailableMoney): return {"available_money": {"token": token_to_json(v.token), "party": party_to_str(v.party)}}
    if isinstance(v, ChoiceValue): return {"choice_value": choice_id_to_json(v.choice_id)}
    if isinstance(v, TimeIntervalStart): return "time_interval_start"
    if isinstance(v, TimeIntervalEnd): return "time_interval_end"
    if isinstance(v, UseValue): return {"use_value": v.value_id}
    if isinstance(v, Cond): return {"if": observation_to_json(v.condition), "then": value_to_json(v.true_value), "else": value_to_json(v.false_value)}
    raise ValueError(f"UnsupportedValue({type(v)})")


# --------------------------
# Main parser (FIXED - Added token_type_str)
# --------------------------

InfosDict = Dict[str, List[Any]]

def parse_contract_to_infos(
    contract: Contract,
    stage: int,
    infos: Optional[InfosDict] = None
) -> Tuple[InfosDict, int]:
    """遞迴地剖析合約，分配 stage 編號，並儲存 token type string"""

    if infos is None:
        infos = {
            "pay": [], "deposit": [], "choice": [], "notify": [],
            "when": [], "if": [], "let": [], "assert": [], "close": [],
        }

    if isinstance(contract, Close):
        infos["close"].append(CloseStageInfo(stage=stage))
        return (infos, stage + 1)

    if isinstance(contract, Pay):
        token_info_json = token_to_json(contract.token)
        move_token_type = marlowe_token_to_move_type(token_info_json)
        infos["pay"].append(PayStageInfo(
            stage=stage,
            from_account=party_to_str(contract.from_account),
            to=payee_to_str(contract.to),
            token=token_info_json,
            amount=value_to_json(contract.value),
            next_stage=stage + 1,
            token_type_str=move_token_type
        ))
        return parse_contract_to_infos(contract.then, stage + 1, infos)

    if isinstance(contract, Let):
        infos["let"].append(LetStageInfo(
            stage=stage,
            name=contract.name,
            value=value_to_json(contract.value)
        ))
        return parse_contract_to_infos(contract.then, stage + 1, infos)

    if isinstance(contract, Assert):
        infos["assert"].append(AssertStageInfo(
            stage=stage,
            observation=observation_to_json(contract.obs)
        ))
        return parse_contract_to_infos(contract.then, stage + 1, infos)

    if isinstance(contract, If):
        then_stage_start = stage + 1
        (infos, then_stage_end) = parse_contract_to_infos(contract.then, then_stage_start, infos)
        else_stage_start = then_stage_end
        (infos, else_stage_end) = parse_contract_to_infos(contract.else_, else_stage_start, infos)
        infos["if"].append(IfStageInfo(
            stage=stage,
            condition=observation_to_json(contract.cond),
            then_stage=then_stage_start,
            else_stage=else_stage_start
        ))
        return (infos, else_stage_end)

    if isinstance(contract, When):
        next_child_stage = stage + 1
        case_next_stages = []
        for case in contract.cases:
            case_starts_at = next_child_stage
            case_next_stages.append(case_starts_at)
            (infos, case_end_stage) = parse_contract_to_infos(case.then, case_starts_at, infos)
            next_child_stage = case_end_stage

        timeout_stage_start = next_child_stage
        (infos, timeout_stage_end) = parse_contract_to_infos(contract.timeout_continuation, timeout_stage_start, infos)

        infos["when"].append(WhenStageInfo(
            stage=stage,
            timeout=contract.timeout,
            cases_count=len(contract.cases),
            timeout_stage=timeout_stage_start
        ))

        for i, case in enumerate(contract.cases):
            act = case.action
            case_next_stage = case_next_stages[i]

            if isinstance(act, Deposit):
                token_info_json = token_to_json(act.token)
                move_token_type = marlowe_token_to_move_type(token_info_json) # (NEW)
                infos["deposit"].append(DepositStageInfo(
                    stage=stage,
                    case_index=i,
                    party=party_to_str(act.party),
                    into_account=party_to_str(act.into_account),
                    token=token_info_json,
                    value=value_to_json(act.amount),
                    next_stage=case_next_stage,
                    token_type_str=move_token_type # (NEW)
                ))
            elif isinstance(act, Choice):
                cid_obj = getattr(act, "choice_id", None)
                owner = getattr(cid_obj, "by", None)
                infos["choice"].append(ChoiceStageInfo(
                    stage=stage,
                    case_index=i,
                    choice_name=getattr(cid_obj, "name", "unknown"),
                    by=party_to_str(owner) if owner else "unknown",
                    bounds=[bound_to_json(b) for b in act.bounds],
                    next_stage=case_next_stage
                ))
            elif isinstance(act, Notify):
                infos["notify"].append(NotifyStageInfo(
                    stage=stage,
                    case_index=i,
                    observation=observation_to_json(act.observation),
                    next_stage=case_next_stage
                ))

        return (infos, timeout_stage_end)

    infos.setdefault("unknown", []).append(str(contract))
    return (infos, stage + 1)


# --------------------------
# JSON output helper
# --------------------------
def infos_to_json(infos: InfosDict) -> str:
    """使用 dataclasses.asdict 進行序列化"""
    out = {}
    for k, lst in infos.items():
        # Ensure item is a dataclass instance before calling asdict
        out[k] = [asdict(item) for item in lst if hasattr(item, '__dataclass_fields__')]
    return json.dumps(out, indent=2, ensure_ascii=False)


# --------------------------
# Example usage (用於測試)
# --------------------------
if __name__ == "__main__":
    try:
        with open("swap_ada.json") as f: # Use your test JSON file
            json_data = json.load(f)
        contract_ast = parse_contract(json_data)
        (infos, next_stage) = parse_contract_to_infos(contract_ast, stage=0)
        print(f"--- Contract Stage Infos (Total stages: {next_stage}) ---")
        print(infos_to_json(infos))

    except FileNotFoundError:
        print("Error: swap_ada.json not found.")
    except Exception as e:
        print(f"Error processing contract: {e}")
        raise
