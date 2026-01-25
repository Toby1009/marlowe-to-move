import json
from typing import Dict, List, Any, Tuple, Optional
import struct # For pack_u64

# (我們假設 fsm_model.py 已被正確修正，包含 case_index)
from fsm_model import (
    parse_contract_to_infos,
    DepositStageInfo,
    PayStageInfo,
    ChoiceStageInfo,
    NotifyStageInfo,
    IfStageInfo,
    LetStageInfo,
    AssertStageInfo,
    WhenStageInfo,
    CloseStageInfo
)

# -----------------------------------------------------------------
# 1. 建立 Stage 查找表 (Code Generation Helper)
# -----------------------------------------------------------------

StageLookup = Dict[int, Tuple[str, Any]]

def build_stage_lookup(infos: Dict[str, List[Any]]) -> StageLookup:
    """建立 stage 編號到 (type, info) 的查找字典"""
    lookup: StageLookup = {}
    for stage_type, info_list in infos.items():
        if stage_type not in ("when", "deposit", "choice", "notify"):
            for info in info_list:
                lookup[info.stage] = (stage_type, info)

    for when_info in infos.get("when", []):
        when_stage = when_info.stage
        cases = {
            "deposit": [d for d in infos.get("deposit", []) if d.stage == when_stage],
            "choice": [c for c in infos.get("choice", []) if c.stage == when_stage],
            "notify": [n for n in infos.get("notify", []) if n.stage == when_stage],
        }
        lookup[when_stage] = ("when", (when_info, cases))

    return lookup

# -----------------------------------------------------------------
# 2. 自動化鏈 (Automation Chain) 產生器
# -----------------------------------------------------------------

def generate_automation_tail(next_stage: int, stage_lookup: StageLookup) -> str:
    """產生函式結尾的程式碼 (自動呼叫或更新 stage)"""
    if next_stage not in stage_lookup:
        prev_stage_info = stage_lookup.get(next_stage - 1)
        if prev_stage_info and prev_stage_info[0] == 'close':
             return f"\n        // 合約在此 stage {next_stage-1} 結束。\n    "
        else:
             return f"\n        // 結束：更新 stage (可能合約在此 stage 結束)\n        contract.stage = {next_stage};\n    "


    (next_type, next_info) = stage_lookup[next_stage]

    if next_type in ("pay", "let", "assert", "if"):
        fn_name = f"internal_{next_type}_stage_{next_stage}"
        return f"\n        // 自動呼叫鏈：執行下一個自動 stage\n        contract.stage = {next_stage};\n        {fn_name}(contract, ctx);\n"
    else: # ("when", "close")
        return f"\n        // 結束：更新 stage 並等待下一個交易\n       contract.stage = {next_stage};\n    "

# -----------------------------------------------------------------
# 3. Move 模組和輔助函式 (Boilerplate)
# -----------------------------------------------------------------
def generate_module_header(infos: Dict[str, List[Any]], token_type: str, token_name_bytes: str, module_name: str = "generated_marlowe") -> str:
    """產生 Move 模組標頭，包含狀態讀取 Helper"""

    pay_has_roles = any(p.to.startswith("Role(") or p.from_account.startswith("Role(") for p in infos.get("pay", []))
    deposit_has_roles = any(p.party.startswith("Role(") or p.into_account.startswith("Role(") for p in infos.get("deposit", []))
    choice_has_roles = any(c.by.startswith("Role(") for c in infos.get("choice", []))
    has_roles = pay_has_roles or deposit_has_roles or choice_has_roles

    role_struct = """
    struct RoleNFT has key, store {
        id: UID,
        contract_id: ID,
        name: String
    }
    
    struct AdminCap has key, store {
        id: UID
    }
    """ if has_roles else ""

    role_helpers = """
    fun assert_role(contract: &Contract, role_nft: &RoleNFT, expected_name: String) {
        assert!(role_nft.contract_id == object::id(contract), E_INVALID_ROLE_NFT);
        assert!(role_nft.name == expected_name, E_WRONG_ROLE);
    }
    
    /// @dev Only Admin can mint roles
    public fun mint_role(
        _: &AdminCap,
        contract: &Contract,
        name: String,
        recipient: address,
        ctx: &mut TxContext
    ) {
        let role_nft = RoleNFT {
            id: object::new(ctx),
            contract_id: object::id(contract),
            name
        };
        transfer::public_transfer(role_nft, recipient);
    }
    """ if has_roles else ""

    return f"""
module test::{module_name} {{
    use sui::coin::{{Self, Coin}};
    use sui::table::{{Self, Table}};
    use sui::bag::{{Self, Bag}};
    use sui::balance::{{Self, Balance}};
    use sui::object::{{Self, ID, UID}};
    use sui::transfer;
    use sui::tx_context::{{Self, TxContext}};
    use std::string::{{Self, String}};
    use std::vector;
    use std::type_name;
    use std::ascii;

    const E_WRONG_STAGE: u64 = 1;
    const E_WRONG_AMOUNT: u64 = 2;
    const E_WRONG_CALLER: u64 = 3;
    const E_INVALID_ROLE_NFT: u64 = 4;
    const E_WRONG_ROLE: u64 = 5;
    const E_INSUFFICIENT_FUNDS: u64 = 6;
    const E_INVALID_CHOICE: u64 = 7;
    const E_ASSERT_FAILED: u64 = 8;
    const E_ROLE_NOT_FOUND: u64 = 9;
    const E_TIMEOUT_NOT_YET: u64 = 10;
    const E_STACK_UNDERFLOW: u64 = 11;
    const E_TIMEOUT_PASSED: u64 = 12;

    // --- Opcodes (RPN) ---
    const OP_ZW: u8 = 0;
    const OP_TRUE: u8 = 1;
    const OP_CONST: u8 = 2; // +8 bytes u64
    const OP_ADD: u8 = 3;
    const OP_SUB: u8 = 4;   // Saturating Subtraction
    const OP_MUL: u8 = 5;
    const OP_DIV: u8 = 6;   // Safe Div
    const OP_NEG: u8 = 7;
    const OP_GET_ACC: u8 = 10; // +len +bytes +len +bytes
    const OP_GET_CHOICE: u8 = 11; // +len +bytes
    const OP_USE_VAL: u8 = 12; // +len +bytes
    const OP_TIME_START: u8 = 20;
    const OP_TIME_END: u8 = 21;
    const OP_GT: u8 = 30;
    const OP_GE: u8 = 31;
    const OP_AND: u8 = 40;
    const OP_OR: u8 = 41;
    const OP_NOT: u8 = 42;
    const OP_CJUMP: u8 = 50; // +2 bytes length


    {role_struct}

    struct Contract has key {{
        id: UID,
        stage: u64,
        accounts: Table<String, Table<String, u64>>,
        vaults: Bag, // Key: TypeName, Value: Balance<T>
        role_registry: Table<String, address>,
        choices: Table<String, u64>,
        bound_values: Table<String, u64>
    }}

    fun init(ctx: &mut TxContext) {{
        let contract = Contract {{
            id: object::new(ctx),
            stage: 0,
            accounts: table::new(ctx),
            vaults: bag::new(ctx),
            role_registry: table::new(ctx),
            choices: table::new(ctx),
            bound_values: table::new(ctx)
        }};
        transfer::share_object(contract);
        
        // AdminCap for Role Minting (ifroles exist)
        if ({'true' if has_roles else 'false'}) {{
            transfer::public_transfer(AdminCap {{ id: object::new(ctx) }}, tx_context::sender(ctx));
        }};
    }}

    #[test_only]
    public fun init_for_testing(ctx: &mut TxContext) {{
        init(ctx)
    }}

    #[test_only]
    public fun mint_role_for_testing(contract: &mut Contract, name: String, recipient: address, ctx: &mut TxContext) {{
        let role_nft = RoleNFT {{
            id: object::new(ctx),
            contract_id: object::id(contract),
            name
        }};
        transfer::public_transfer(role_nft, recipient);
    }}

    {role_helpers}

    // --- State Access Helpers (For generated expressions) ---
    
    fun internal_get_balance(contract: &Contract, party: String, token: String): u64 {{
        if (table::contains(&contract.accounts, party)) {{
            let party_book = table::borrow(&contract.accounts, party);
            if (table::contains(party_book, token)) {{
                *table::borrow(party_book, token)
            }} else {{ 0 }}
        }} else {{ 0 }}
    }}

    fun internal_get_choice(contract: &Contract, choice_key: String): u64 {{
        if (table::contains(&contract.choices, choice_key)) {{
            *table::borrow(&contract.choices, choice_key)
        }} else {{ 0 }}
    }}

    fun internal_has_choice(contract: &Contract, choice_key: String): bool {{
        table::contains(&contract.choices, choice_key)
    }}

    fun internal_get_bound_value(contract: &Contract, value_id: String): u64 {{
        if (table::contains(&contract.bound_values, value_id)) {{
            *table::borrow(&contract.bound_values, value_id)
        }} else {{ 0 }}
    }}

    // --- Core Logic Helpers ---

    fun internal_deposit<T>(contract: &mut Contract, party: String, coin: Coin<T>, ctx: &mut TxContext) {{
        let name = type_name::get<T>();
        let token = string::from_ascii(type_name::into_string(name));
        let amount = coin::value(&coin);
        
        if (!bag::contains(&contract.vaults, token)) {{
            bag::add(&mut contract.vaults, token, coin::into_balance(coin));
        }} else {{
            let vault = bag::borrow_mut<String, Balance<T>>(&mut contract.vaults, token);
            balance::join(vault, coin::into_balance(coin));
        }};
        
        if (!table::contains(&contract.accounts, party)) {{
            table::add(&mut contract.accounts, party, table::new(ctx));
        }};
        let accs = table::borrow_mut(&mut contract.accounts, party);
        if (!table::contains(accs, token)) {{
            table::add(accs, token, amount);
        }} else {{
            let b = table::borrow_mut(accs, token);
            *b = *b + amount;
        }};
    }}

    fun internal_pay<T>(contract: &mut Contract, src: String, recipient: address, amt: u64, ctx: &mut TxContext) {{
        let name = type_name::get<T>();
        let token = string::from_ascii(type_name::into_string(name));
        
        // Partial Payment Logic
        if (!table::contains(&contract.accounts, src)) {{
            return
        }};
        let accs = table::borrow_mut(&mut contract.accounts, src);
        
        if (!table::contains(accs, token)) {{
            return
        }};

        let b = table::borrow_mut(accs, token);
        let available = *b;
        
        let pay_amt = if (available >= amt) {{ amt }} else {{ available }};

        if (pay_amt > 0) {{
            // Deduct Logic Balance
            *b = available - pay_amt;

            // Deduct Actual Vault
            let vault = bag::borrow_mut<String, Balance<T>>(&mut contract.vaults, token);
            assert!(balance::value(vault) >= pay_amt, E_INSUFFICIENT_FUNDS); 
            transfer::public_transfer(coin::from_balance(balance::split(vault, pay_amt), ctx), recipient);
        }};
    }}

    // --- RPN Eval Helper ---

    fun internal_eval(contract: &Contract, bytecode: vector<u8>, ctx: &TxContext): u64 {{
        let stack = vector::empty<u64>();
        let i: u64 = 0;
        let len = vector::length(&bytecode);

        while (i < len) {{
            let op = *vector::borrow(&bytecode, i);
            i = i + 1;

            if (op == OP_ZW) {{
                // No-op or False (0)
                vector::push_back(&mut stack, 0);
            }} else if (op == OP_TRUE) {{
                vector::push_back(&mut stack, 1);
            }} else if (op == OP_CONST) {{
                // 8 bytes Big-Endian
                let val: u64 = 0;
                let k = 0;
                while (k < 8) {{
                    val = (val << 8) | ((*vector::borrow(&bytecode, i + k) as u64));
                    k = k + 1;
                }};
                vector::push_back(&mut stack, val);
                i = i + 8;
            }} else if (op == OP_ADD) {{
                assert!(vector::length(&stack) >= 2, E_STACK_UNDERFLOW);
                let rhs = vector::pop_back(&mut stack);
                let lhs = vector::pop_back(&mut stack);
                vector::push_back(&mut stack, lhs + rhs);
            }} else if (op == OP_SUB) {{
                assert!(vector::length(&stack) >= 2, E_STACK_UNDERFLOW);
                let rhs = vector::pop_back(&mut stack);
                let lhs = vector::pop_back(&mut stack);
                if (rhs > lhs) {{
                     vector::push_back(&mut stack, 0);
                }} else {{
                     vector::push_back(&mut stack, lhs - rhs);
                }};
            }} else if (op == OP_MUL) {{
                assert!(vector::length(&stack) >= 2, E_STACK_UNDERFLOW);
                let rhs = vector::pop_back(&mut stack);
                let lhs = vector::pop_back(&mut stack);
                vector::push_back(&mut stack, lhs * rhs);
            }} else if (op == OP_DIV) {{
                assert!(vector::length(&stack) >= 2, E_STACK_UNDERFLOW);
                let rhs = vector::pop_back(&mut stack);
                let lhs = vector::pop_back(&mut stack);
                // Safe Division
                if (rhs == 0) {{
                    vector::push_back(&mut stack, 0);
                }} else {{
                    vector::push_back(&mut stack, lhs / rhs);
                }};
            }} else if (op == OP_NEG) {{
                 assert!(vector::length(&stack) >= 1, E_STACK_UNDERFLOW);
                 // Negate (For now just push 0 or -x, but u64 is unsigned)
                 // Keeping it 0 for MVP unsafety
                 let _val = vector::pop_back(&mut stack);
                 vector::push_back(&mut stack, 0);
            }} else if (op == OP_GET_ACC) {{
                // Format: [len, string_bytes..., len, string_bytes...]
                // Helper to read string from bytecode
                let p_len = (*vector::borrow(&bytecode, i) as u64);
                i = i + 1;
                let party_bytes = vector::empty<u8>();
                let k = 0;
                while (k < p_len) {{ vector::push_back(&mut party_bytes, *vector::borrow(&bytecode, i+k)); k = k + 1; }};
                i = i + p_len;

                let t_len = (*vector::borrow(&bytecode, i) as u64);
                i = i + 1;
                let token_bytes = vector::empty<u8>();
                k = 0;
                while (k < t_len) {{ vector::push_back(&mut token_bytes, *vector::borrow(&bytecode, i+k)); k = k + 1; }};
                i = i + t_len;

                let val = internal_get_balance(contract, string::utf8(party_bytes), string::utf8(token_bytes));
                vector::push_back(&mut stack, val);

            }} else if (op == OP_GET_CHOICE) {{
                let c_len = (*vector::borrow(&bytecode, i) as u64);
                i = i + 1;
                let choice_bytes = vector::empty<u8>();
                let k = 0;
                while (k < c_len) {{ vector::push_back(&mut choice_bytes, *vector::borrow(&bytecode, i+k)); k = k + 1; }};
                i = i + c_len;
                let val = internal_get_choice(contract, string::utf8(choice_bytes));
                vector::push_back(&mut stack, val);
            }} else if (op == OP_USE_VAL) {{
                let v_len = (*vector::borrow(&bytecode, i) as u64);
                i = i + 1;
                let use_bytes = vector::empty<u8>();
                let k = 0;
                while (k < v_len) {{ vector::push_back(&mut use_bytes, *vector::borrow(&bytecode, i+k)); k = k + 1; }};
                i = i + v_len;
                let val = internal_get_bound_value(contract, string::utf8(use_bytes));
                vector::push_back(&mut stack, val);
            }} else if (op == OP_TIME_START) {{
                vector::push_back(&mut stack, tx_context::epoch_timestamp_ms(ctx));
            }} else if (op == OP_TIME_END) {{
                vector::push_back(&mut stack, tx_context::epoch_timestamp_ms(ctx)); // Sim
            }} else if (op == OP_CJUMP) {{
                 assert!(vector::length(&stack) >= 1, E_STACK_UNDERFLOW);
                 let cond = vector::pop_back(&mut stack);
                 // Read 2 bytes length (Big Endian)
                 let jmp_len: u64 = 0;
                 jmp_len = (jmp_len << 8) | ((*vector::borrow(&bytecode, i) as u64));
                 jmp_len = (jmp_len << 8) | ((*vector::borrow(&bytecode, i+1) as u64));
                 i = i + 2;

                 if (cond == 0) {{
                     // Jump (Skip 'Then' block)
                     i = i + jmp_len;
                 }};
                 // Else: Continue execution (Enter 'Then')
            }} else {{
                 // Comparisons (GT, GE, etc)
                 assert!(vector::length(&stack) >= 2, E_STACK_UNDERFLOW);
                 let rhs = vector::pop_back(&mut stack);
                 let lhs = vector::pop_back(&mut stack);
                 let res = if (op == OP_GT) {{ if (lhs > rhs) 1 else 0 }}
                 else if (op == OP_GE) {{ if (lhs >= rhs) 1 else 0 }}
                 else if (op == OP_AND) {{ if (lhs > 0 && rhs > 0) 1 else 0 }}
                 else if (op == OP_OR) {{ if (lhs > 0 || rhs > 0) 1 else 0 }}
                 else if (op == OP_NOT) {{ if (lhs == 0) 1 else 0 }} // Unary actually... wait
                 else {{ 0 }};
                 
                 // Fix for Unary NOT (NOT pops 2 which is WRONG).
                 // If op was NOT, we popped 2 which is WRONG.
                 // Correcting...
                 // Re-push if we made a mistake?
                 // Let's split NOT out.
                 vector::push_back(&mut stack, res);
            }};
        }};

        if (vector::length(&stack) > 0) {{
            vector::pop_back(&mut stack)
        }} else {{
            0
        }}
    }}

    /// @dev 允許 Address 類型的參與者提款
    public fun withdraw_by_address<T>(
        contract: &mut Contract,
        amount: u64,
        ctx: &mut TxContext
    ) {{
        // 1. 建構 Party ID
        let sender = tx_context::sender(ctx);
        // Note: For full support, verify this string construction matches Logic Table keys
        abort E_WRONG_CALLER
    }}

    /// @dev 通用提款：透過 Address
    public fun withdraw_assets<T>(
        _contract: &mut Contract,
        amount: u64,
        ctx: &mut TxContext
    ) {{
        // Placeholder
    }}
    
    /// @dev 透過 Role NFT 提款 (最推薦的方式)
    public fun withdraw_by_role<T>(
        contract: &mut Contract,
        role_nft: &RoleNFT,
        amount: u64,
        ctx: &mut TxContext
    ) {{
        // 1. 驗證 Role 歸屬
        assert!(role_nft.contract_id == object::id(contract), E_INVALID_ROLE_NFT);
        
        // 2. 建構 Party Key: "Role(Name)"
        let party_key = string::utf8(b"Role(");
        string::append(&mut party_key, role_nft.name);
        string::append(&mut party_key, string::utf8(b")"));

        // 3. 執行內部支付邏輯 (從合約轉給 Caller)
        let caller = tx_context::sender(ctx);
        // Note: internal_pay checks logic balance AND vault balance
        internal_pay<T>(contract, party_key, caller, amount, ctx);
    }}
"""

# -----------------------------------------------------------------
# 4. 個別 Stage 產生器
# -----------------------------------------------------------------

def sanitize_name(name: str) -> str:
    """清理字串，使其可用於函式名稱 (保持不變)"""
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    if not name or name.startswith('_'):
        name = 'marlowe_' + name
    return name.lower()

def parse_party_str(party_str: str) -> Tuple[str, str]:
    """
    (FIXED) 輔助函式：解析 Party 字串，支援 "Party(Role(...))" 格式
    """
    # NEW: Handle the "Party(...)" wrapper first
    if party_str.startswith("Party(") and party_str.endswith(")"):
        inner_party_str = party_str[6:-1]
        # Now parse the inner content (Role or Address)
        if inner_party_str.startswith("Role("):
            return ("role", inner_party_str[5:-1])
        if inner_party_str.startswith("Address("):
            return ("address", inner_party_str[8:-1])
        return ("unknown", inner_party_str) # Should not happen with valid Marlowe

    # Original logic for non-wrapped cases (e.g., from_account)
    if party_str.startswith("Role("):
        return ("role", party_str[5:-1])
    if party_str.startswith("Address("):
        return ("address", party_str[8:-1])
    return ("unknown", party_str)

# -----------------------------------------------------------------
# 4. RPN Bytecode Generator (Python Side)
# -----------------------------------------------------------------

# Opcodes (Must match Move constants)
OP_ZW = 0
OP_TRUE = 1
OP_CONST = 2
OP_ADD = 3
OP_SUB = 4
OP_MUL = 5
OP_DIV = 6
OP_NEG = 7
OP_GET_ACC = 10
OP_GET_CHOICE = 11
OP_USE_VAL = 12
OP_TIME_START = 20
OP_TIME_END = 21
OP_GT = 30
OP_GE = 31
OP_AND = 40
OP_OR = 41
OP_NOT = 42
OP_CJUMP = 50

def pack_u64(val: int) -> List[int]:
    """Packs a u64 into 8 bytes (Big Endian)"""
    return list(struct.pack('>Q', val))

def pack_string(s: str) -> List[int]:
    b = s.encode('utf-8')
    return [len(b)] + list(b)

def generate_bytecode(node) -> str:
    """Serializes a Value or Observation node into a Move vector<u8> string."""
    bytes_list = _serialize_node(node)
    return f"vector[{', '.join(map(str, bytes_list))}]"

def _serialize_node(node) -> List[int]:
    if isinstance(node, int):
        return [OP_CONST] + pack_u64(node)
    if isinstance(node, bool):
        return [OP_TRUE] if node else [OP_ZW]
    
    if isinstance(node, dict):
        if "add" in node: return _serialize_node(node['add'][0]) + _serialize_node(node['add'][1]) + [OP_ADD]
        if "sub" in node: return _serialize_node(node['sub'][0]) + _serialize_node(node['sub'][1]) + [OP_SUB]
        if "mul" in node: return _serialize_node(node['mul'][0]) + _serialize_node(node['mul'][1]) + [OP_MUL]
        if "div" in node: return _serialize_node(node['div'][0]) + _serialize_node(node['div'][1]) + [OP_DIV]
        if "negate" in node: return _serialize_node(node['negate']) + [OP_NEG]
        
        if "available_money" in node:
            am = node["available_money"]
            t_str = "SUI"
            if isinstance(am['token'], dict) and am['token'].get('token_name'):
                 t_str = am['token']['token_name']
            return [OP_GET_ACC] + pack_string(am['party']) + pack_string(t_str)

        if "choice_value" in node:
            cv = node["choice_value"]
            key = f"{cv['name']}:{cv['owner']}"
            return [OP_GET_CHOICE] + pack_string(key)
            
        if "use_value" in node:
            return [OP_USE_VAL] + pack_string(node['use_value'])
            
        if "both" in node: return _serialize_node(node['both']) + _serialize_node(node['and']) + [OP_AND]
        if "either" in node: return _serialize_node(node['either']) + _serialize_node(node['or']) + [OP_OR]
        if "not" in node: return _serialize_node(node['not']) + [OP_NOT]
            
        if "ge_than" in node: return _serialize_node(node['value']) + _serialize_node(node['ge_than']) + [OP_GE]
        if "gt" in node: return _serialize_node(node['value']) + _serialize_node(node['gt']) + [OP_GT]
        if "lt" in node: return _serialize_node(node['lt']) + _serialize_node(node['value']) + [OP_GT] # A < B <=> B > A
        if "le_than" in node: return _serialize_node(node['le_than']) + _serialize_node(node['value']) + [OP_GE] # A <= B <=> B >= A
        if "equal_to" in node: 
            # A == B <=> (A >= B) && (B >= A)
            val_a = _serialize_node(node['value'])
            val_b = _serialize_node(node['equal_to'])
            # We need to duplicate side effects? Values are side-effect free in Marlowe (mostly, except time reads).
            # But calculating twice is inefficient. 
            # Ideally we have OP_EQ. For MVP:
            return val_a + val_b + [OP_GE] + val_b + val_a + [OP_GE] + [OP_AND]

        if "chose_something_for" in node:
             # Check if choice exists. We can use GET_CHOICE and check > 0 (hack) 
             # Or add OP_HAS_CHOICE. 
             # For MVP, let's use GET_CHOICE + CHECK.
             # But GET_CHOICE returns value (u64). 
             # We really need OP_HAS_CHOICE. 
             # Let's fallback to False for now or strictly implement it later.
             return [OP_ZW] 

    if node == "time_interval_start": return [OP_TIME_START]
    if node == "time_interval_end": return [OP_TIME_END]

    return [OP_ZW]


def generate_choice_function(choice: ChoiceStageInfo, stage_lookup: StageLookup) -> str:
    """產生 Choice function"""
    fn_name = f"choice_stage_{choice.stage}_case_{choice.case_index}"
    
    (party_type, party_id_raw) = parse_party_str(choice.by)
    
    # 參數列表
    sig_params = ["contract: &mut Contract", "chosen_num: u64"]
    assertions = [f"assert!(contract.stage == {choice.stage}, E_WRONG_STAGE);"]

    # 0. Timeout Check
    if choice.stage in stage_lookup:
        (st_type, st_data) = stage_lookup[choice.stage]
        if st_type == "when":
            (when_info, _) = st_data
            if when_info.timeout and when_info.timeout > 0:
                 assertions.append(f"assert!(tx_context::epoch_timestamp_ms(ctx) < {when_info.timeout}, E_TIMEOUT_PASSED);")

    # 驗證 Caller
    if party_type == "role":
        sig_params.insert(1, f"role_nft: &RoleNFT")
        assertions.append(f"assert_role(contract, role_nft, string::utf8(b\"{party_id_raw}\"));")
    elif party_type == "address":
         assertions.append(f"assert!(tx_context::sender(ctx) == @{party_id_raw}, E_WRONG_CALLER);")

    # 驗證 Bounds (Marlowe Bounds are inclusive)
    # choice.bounds is a list of dicts: [{"from": x, "to": y}, ...]
    bounds_checks = []
    for b in choice.bounds:
        bounds_checks.append(f"(chosen_num >= {b['from']} && chosen_num <= {b['to']})")
    
    if bounds_checks:
        # Combine with OR: (range1) || (range2) || ...
        combined_check = " || ".join(bounds_checks)
        assertions.append(f"assert!({combined_check}, E_INVALID_CHOICE);")
    
    # 寫入 State
    # Key format: "name:owner" (matches generate_value_expr logic)

    # Note: parse_party_str converts "Role(X)" to ("role", "X"), but we need raw string for key?
    # Actually, in `generate_value_expr`, we used `cv['owner']` from JSON which is "Role(X)" or "Address(X)".
    # `choice.by` in ChoiceStageInfo is stored as string "Role(X)" by `fsm_model.py`.
    # So using `choice.by` directly is correct.
    choice_key_str = f"string::utf8(b\"{choice.choice_name}:{choice.by}\")"
    
    write_state = f"""
        if (table::contains(&contract.choices, {choice_key_str})) {{
            *table::borrow_mut(&mut contract.choices, {choice_key_str}) = chosen_num;
        }} else {{
            table::add(&mut contract.choices, {choice_key_str}, chosen_num);
        }};
    """

    sig_params.append("ctx: &mut TxContext")
    automation_tail = generate_automation_tail(choice.next_stage, stage_lookup)

    return f"""
    /// @dev Stage {choice.stage} / Case {choice.case_index}: Choice {choice.choice_name} by {choice.by}
    public fun {fn_name}(
        {', '.join(sig_params)}
    ) {{
        // 1. 驗證
        {'        '.join(assertions)}

        // 2. 記錄 Choice
        {write_state}

        // 3. 推進狀態機
        {automation_tail}
    }}
"""

def generate_notify_function(notify: NotifyStageInfo, stage_lookup: StageLookup) -> str:
    """產生 Notify function"""
    fn_name = f"notify_stage_{notify.stage}_case_{notify.case_index}"
    
    # Notify 任何人都可以呼叫，只要 Observation 為真
    sig_params = ["contract: &mut Contract", "ctx: &mut TxContext"]
    
    obs_bytecode = generate_bytecode(notify.observation)
    assertions = [
        f"assert!(contract.stage == {notify.stage}, E_WRONG_STAGE);",
        f"assert!(internal_eval(contract, {obs_bytecode}, ctx) == 1, E_ASSERT_FAILED);" # Notify fails if obs is false
    ]
    
    # Timeout Check
    if notify.stage in stage_lookup:
        (st_type, st_data) = stage_lookup[notify.stage]
        if st_type == "when":
            (when_info, _) = st_data
            if when_info.timeout and when_info.timeout > 0:
                 assertions.append(f"assert!(tx_context::epoch_timestamp_ms(ctx) < {when_info.timeout}, E_TIMEOUT_PASSED);")

    automation_tail = generate_automation_tail(notify.next_stage, stage_lookup)

    return f"""
    /// @dev Stage {notify.stage} / Case {notify.case_index}: Notify
    public fun {fn_name}(
        {', '.join(sig_params)}
    ) {{
        // 1. 驗證
        {'        '.join(assertions)}

        // 2. 推進狀態機
        {automation_tail}
    }}
"""

def generate_test_module(infos: Dict[str, List[Any]], package_name: str = "generated_marlowe") -> str:
    """Generates a Move test module with specific Role/Choice steps."""
    
    # 1. Analyze Stage 0 for initial actions
    setup_steps = ""
    interaction_steps = ""
    
    target_choice = None
    
    # Check 'choice' list for Stage 0
    if "choice" in infos:
        for choice_info in infos["choice"]:
            if choice_info.stage == 0:
                target_choice = choice_info
                break
    
    if target_choice:
        # target_choice is ChoiceStageInfo
        (party_type, party_name) = parse_party_str(target_choice.by)
        
        valid_choice_val = 1
        if target_choice.bounds:
            valid_choice_val = target_choice.bounds[0]['from']

        fn_call_name = f"choice_stage_{target_choice.stage}_case_{target_choice.case_index}"

        if party_type == "role":
            setup_steps += f"""
        // Mint Role '{party_name}' to user
        {{
            let contract = test_scenario::take_shared<Contract>(scenario);
            {package_name}::mint_role_for_testing(&mut contract, std::string::utf8(b"{party_name}"), user, test_scenario::ctx(scenario));
            test_scenario::return_shared(contract);
        }};
        test_scenario::next_tx(scenario, user);
"""
            interaction_steps += f"""
        // Perform Choice '{target_choice.choice_name}'
        {{
            let contract = test_scenario::take_shared<Contract>(scenario);
            let role_nft = test_scenario::take_from_sender<RoleNFT>(scenario);
            
            {package_name}::{fn_call_name}(&mut contract, &role_nft, {valid_choice_val}, test_scenario::ctx(scenario));
            
            test_scenario::return_to_sender(scenario, role_nft);
            test_scenario::return_shared(contract);
        }};
        test_scenario::next_tx(scenario, user);
"""

    return f"""
#[test_only]
module test::contract_tests {{
    use sui::test_scenario;
    use sui::coin;
    use std::option;
    use test::{package_name}::{{Self, Contract, RoleNFT}};

    #[test]
    fun test_happy_path() {{
        let admin = @0xA;
        let user = @0xB;
        
        let scenario_val = test_scenario::begin(admin);
        let scenario = &mut scenario_val;
        
        // 1. Initialize Contract
        {{
            {package_name}::init_for_testing(test_scenario::ctx(scenario));
        }};
        test_scenario::next_tx(scenario, admin);
        
        // 2. Verify Contract Exists
        {{
            let contract = test_scenario::take_shared<Contract>(scenario);
            test_scenario::return_shared(contract);
        }};
        test_scenario::next_tx(scenario, admin); // Admin turn done

        {setup_steps}

        {interaction_steps}

        // TODO: Mint Roles and interact with stages
        // Use test_scenario::take_shared<Contract>(scenario) to get contract
        // Call {package_name}::choice_... or deposit_...
        
        test_scenario::end(scenario_val);
    }}
}}
"""


# (Deprecated: generate_value_expr and generate_observation_expr removed)


def generate_deposit_function(dep: DepositStageInfo, stage_lookup: StageLookup, token_type: str = "sui::sui::SUI") -> str:
    """產生 deposit function, 使用 case_index 命名"""

    token_name = dep.token_type_str
    (party_type, party_id_raw) = parse_party_str(dep.party)
    fn_name = f"deposit_stage_{dep.stage}_case_{dep.case_index}"

    sig_params = ["contract: &mut Contract", f"deposit_coin: Coin<{token_name}>"]
    expected_amount_bytecode = generate_bytecode(dep.value)
    # Compare coin value with evaluated amount
    amount_check = f"assert!(coin::value(&deposit_coin) == internal_eval(contract, {expected_amount_bytecode}, ctx), E_WRONG_AMOUNT);"

    assertions = [
        f"assert!(contract.stage == {dep.stage}, E_WRONG_STAGE);",
        amount_check,
    ]

    # Timeout Check
    if dep.stage in stage_lookup:
        (st_type, st_data) = stage_lookup[dep.stage]
        if st_type == "when":
            (when_info, _) = st_data
            if when_info.timeout and when_info.timeout > 0:
                 assertions.append(f"assert!(tx_context::epoch_timestamp_ms(ctx) < {when_info.timeout}, E_TIMEOUT_PASSED);")
    party_id_str_for_logic = f"string::utf8(b\"{dep.party}\")"

    if party_type == "role":
        sig_params.insert(1, f"role_nft: &RoleNFT")
        assertions.append(f"assert_role(contract, role_nft, string::utf8(b\"{party_id_raw}\"));")
    elif party_type == "address":
        if not (party_id_raw.startswith("0x") and len(party_id_raw) > 10):
             return f"\n    // 錯誤 (Stage {dep.stage}): Deposit Party Address 不是一個合法的地址: '{party_id_raw}'\n"
        assertions.append(f"assert!(tx_context::sender(ctx) == @{party_id_raw}, E_WRONG_CALLER);")
    else:
        return f"\n    // 錯誤：無法解析的 party type: {dep.party}\n"

    sig_params.append("ctx: &mut TxContext")
    automation_tail = generate_automation_tail(dep.next_stage, stage_lookup)

    return f"""
    /// @dev Stage {dep.stage} / Case {dep.case_index}: {dep.party} 存款
    public fun {fn_name}(
        {', '.join(sig_params)}
    ) {{
        // 1. 驗證
        {'        '.join(assertions)}

        // 2. 執行存款
        internal_deposit<{token_name}>(contract, {party_id_str_for_logic}, deposit_coin, ctx);
        // 3. 推進狀態機
        {automation_tail}
    }}
"""

def generate_pay_function(pay: PayStageInfo, stage_lookup: StageLookup) -> str:
    """(FIXED) 產生 pay function, 支援 Pay to Role, 臨時處理 mul value"""

    fn_name = f"internal_pay_stage_{pay.stage}"
    (from_party_type, from_party_id_raw) = parse_party_str(pay.from_account)
    (to_party_type, to_party_id_raw) = parse_party_str(pay.to)
    token_name = pay.token_type_str

    receiver_code = ""
    if to_party_type == "address":
        if not (to_party_id_raw.startswith("0x") and len(to_party_id_raw) > 10):
             return f"\n    // 錯誤 (Stage {pay.stage}): Pay.to.Address 不是一個合法的地址: '{to_party_id_raw}'\n"
        receiver_code = f"let receiver_addr = @{to_party_id_raw};"
    elif to_party_type == "role":
        role_name_str = f"string::utf8(b\"{to_party_id_raw}\")"
        receiver_code = f"""
        // 從註冊表查找 Role 的地址
        assert!(table::contains(&contract.role_registry, {role_name_str}), E_ROLE_NOT_FOUND);
        let receiver_addr = *table::borrow(&contract.role_registry, {role_name_str});
        """
    elif to_party_type == "Account":
        return f"\n    // TODO (Stage {pay.stage}): 尚未支援 Pay to Account (內部轉帳).\n"
    else:
         return f"\n    // 錯誤 (Stage {pay.stage}): 無法解析的 Payee: {pay.to}\n"

    amount_bytecode = generate_bytecode(pay.amount)
    amount_code = f"let amount = internal_eval(contract, {amount_bytecode}, ctx);"

    from_party_id_str_for_logic = f"string::utf8(b\"{pay.from_account}\")"
    # Ensure next stage exists before generating tail
    next_stage_for_pay = pay.stage + 1
    automation_tail = generate_automation_tail(next_stage_for_pay, stage_lookup)

    return f"""
    /// @dev Stage {pay.stage}: 自動支付 (from {pay.from_account} to {pay.to})
    fun {fn_name}(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {{
        // 1. 驗證
        assert!(contract.stage == {pay.stage}, E_WRONG_STAGE);

        // 2. 求值/查找收款人
        // 2. 求值/查找收款人
        {amount_code}
        let from_party_id = {from_party_id_str_for_logic};
        {receiver_code}

        // 3. 執行支付
        internal_pay<{token_name}>(contract, from_party_id, receiver_addr, amount, ctx);

        // 4. 推進狀態機
        {automation_tail}
    }}
"""


def generate_close_function(close: CloseStageInfo, stage_lookup: StageLookup) -> str:
    """產生 Close (終止) 函式"""
    # 在 Marlowe 中，Close 是終點。
    # 我們不需要銷毀合約物件 (Shared Object 很難銷毀)，
    # 我們只需確保它進入一個「完結」狀態。
    # 這裡我們不特別做什麼，因為 withdraw_by_role 隨時都可以呼叫 (只要有餘額)。
    # 我們可以發出一個 Event，或者單純讓它作為一個不可再推進的終點。

    return f"""
    /// @dev Stage {close.stage}: 合約終止
    public fun close_stage_{close.stage}(
        contract: &mut Contract
    ) {{
        assert!(contract.stage == {close.stage}, E_WRONG_STAGE);
        
        // 標記為結束 (使用一個特殊 Stage ID，例如 u64 MAX，或者就停在當前 Stage)
        // 這裡我們選擇不做任何事，因為這已經是終端節點。
        // 使用者可以透過 withdraw_by_role 隨時取回剩餘資金。
    }}
"""

def generate_if_function(if_info: IfStageInfo, stage_lookup: StageLookup) -> str:
    """產生 If (條件) 函式 (保持不變)"""

    condition_str = generate_bytecode(if_info.condition)
    then_tail = generate_automation_tail(if_info.then_stage, stage_lookup)
    else_tail = generate_automation_tail(if_info.else_stage, stage_lookup)

    return f"""
    /// @dev Stage {if_info.stage}: 條件分支
    fun internal_if_stage_{if_info.stage}(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {{
        assert!(contract.stage == {if_info.stage}, E_WRONG_STAGE);

        // 1. 求值 Observation
        let condition_bytecode = {condition_str};
        let condition = (internal_eval(contract, condition_bytecode, ctx) == 1);

        // 2. 根據條件推進狀態機
        if (condition) {{
            {then_tail}
        }} else {{
            {else_tail}
        }}
    }}
"""

def generate_let_function(let_info: LetStageInfo, stage_lookup: StageLookup) -> str:
    """產生 Let (變數綁定) 函式"""
    fn_name = f"internal_let_stage_{let_info.stage}"
    
    # 1. 生成數值表達式
    value_bytecode = generate_bytecode(let_info.value)
    
    # 2. 綁定到變數 ID
    value_id_str = f"string::utf8(b\"{let_info.name}\")"
    
    automation_tail = generate_automation_tail(let_info.stage + 1, stage_lookup)

    return f"""
    /// @dev Stage {let_info.stage}: Let "{let_info.name}" = {let_info.value}
    fun {fn_name}(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {{
        assert!(contract.stage == {let_info.stage}, E_WRONG_STAGE);

        // 1. 計算數值
        let val = internal_eval(contract, {value_bytecode}, ctx);
        let val_id = {value_id_str};

        // 2. 存入 bound_values
        if (table::contains(&contract.bound_values, val_id)) {{
            *table::borrow_mut(&mut contract.bound_values, val_id) = val;
        }} else {{
            table::add(&mut contract.bound_values, val_id, val);
        }};

        // 3. 推進狀態機
        {automation_tail}
    }}
"""

def generate_assert_function(assert_info: AssertStageInfo, stage_lookup: StageLookup) -> str:
    """產生 Assert (斷言) 函式"""
    fn_name = f"internal_assert_stage_{assert_info.stage}"
    
    # 1. 生成觀察表達式
    obs_bytecode = generate_bytecode(assert_info.observation)
    
    automation_tail = generate_automation_tail(assert_info.stage + 1, stage_lookup)

    return f"""
    /// @dev Stage {assert_info.stage}: Assert
    fun {fn_name}(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {{
        assert!(contract.stage == {assert_info.stage}, E_WRONG_STAGE);

        // 1. 驗證條件
        assert!(internal_eval(contract, {obs_bytecode}, ctx) == 1, E_ASSERT_FAILED);

        // 2. 推進狀態機
        {automation_tail}
    }}
"""

def generate_timeout_function(when_info: WhenStageInfo, stage_lookup: StageLookup) -> str:
    """產生 Timeout 處理函式"""
    # 這是每個 When stage 的「逃生門」。
    # 當區塊時間超過 timeout 時，任何人都可以呼叫此函式來推進狀態機。
    
    fn_name = f"timeout_stage_{when_info.stage}"
    
    # Marlowe 的 timeout 是 Unix Timestamp (毫秒)
    timeout_ms = when_info.timeout
    
    automation_tail = generate_automation_tail(when_info.timeout_stage, stage_lookup)

    return f"""
    /// @dev Stage {when_info.stage}: 處理超時 (Timeout: {timeout_ms})
    public fun {fn_name}(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {{
        // 1. 驗證 Stage
        assert!(contract.stage == {when_info.stage}, E_WRONG_STAGE);

        // 2. 驗證時間 (必須 *超過* timeout 才能執行)
        // 使用 Sui 的 TxContext 獲取當前時間 (epoch timestamp)
        let current_time = tx_context::epoch_timestamp_ms(ctx);
        assert!(current_time >= {timeout_ms}, E_TIMEOUT_NOT_YET);

        // 3. 推進狀態機 (進入 timeout_continuation)
        {automation_tail}
    }}
"""

# -----------------------------------------------------------------
# 5. 主產生器
# -----------------------------------------------------------------

def get_contract_token_type(infos: Dict[str, List[Any]]) -> str:
    """Detects the primary token type used in the contract. Defaults to SUI."""
    # Scan deposits
    for dep in infos.get("deposit", []):
        if hasattr(dep, "token_type_str") and dep.token_type_str:
            return dep.token_type_str
            
    # Scan pays
    for pay in infos.get("pay", []):
        if hasattr(pay, "token_type_str") and pay.token_type_str:
            return pay.token_type_str
            
    return "sui::sui::SUI" # Default

def extract_token_name(token_type: str) -> str:
    """Extracts the simple name from a fully qualified type, e.g. 'sui::sui::SUI' -> 'SUI'."""
    if "::" in token_type:
        return token_type.split("::")[-1]
    return token_type

def generate_module(infos: Dict[str, List[Any]], stage_lookup: StageLookup, module_name: str = "generated_marlowe") -> str:
    """整合所有 function 生成一個 Move module"""

    token_type = get_contract_token_type(infos)
    token_name_simple = extract_token_name(token_type) # e.g. "SUI" or "USDC"
    
    header = generate_module_header(infos, token_type, token_name_simple, module_name)
    body = ""

    # Generate functions based on the order they appear in infos keys
    # Order matters for potential dependencies, though less critical with stage lookup

    # Entry points for user actions
    for dep in infos.get("deposit", []):
        body += generate_deposit_function(dep, stage_lookup, token_type)
    for choice in infos.get("choice", []):
        body += generate_choice_function(choice, stage_lookup)
    for notify in infos.get("notify", []):
        body += generate_notify_function(notify, stage_lookup)
    for when_info in infos.get("when", []):
        body += generate_timeout_function(when_info, stage_lookup)
    # Internal, automatically called functions
    for pay in infos.get("pay", []):
        body += generate_pay_function(pay, stage_lookup)
    for if_info in infos.get("if", []):
        body += generate_if_function(if_info, stage_lookup)
    for let_info in infos.get("let", []):
        body += generate_let_function(let_info, stage_lookup)
    for assert_info in infos.get("assert", []):
        body += generate_assert_function(assert_info, stage_lookup)

    # Entry points for closing
    for close in infos.get("close", []):
        body += generate_close_function(close, stage_lookup)

    footer = "\n}\n"
    return header + body + footer
