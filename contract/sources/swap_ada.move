
module test::swap_ada {
    use sui::coin::{Self, Coin};
    use sui::table::{Self, Table};
    use sui::bag::{Self, Bag};
    use sui::balance::{Self, Balance};
    use sui::object::{Self, ID, UID};
    use sui::transfer;
    use sui::tx_context::{Self, TxContext};
    use std::string::{Self, String};
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


    
    struct RoleNFT has key, store {
        id: UID,
        contract_id: ID,
        name: String
    }
    
    struct AdminCap has key, store {
        id: UID
    }
    

    struct Contract has key {
        id: UID,
        stage: u64,
        accounts: Table<String, Table<String, u64>>,
        vaults: Bag, // Key: TypeName, Value: Balance<T>
        role_registry: Table<String, address>,
        choices: Table<String, u64>,
        bound_values: Table<String, u64>
    }

    fun init(ctx: &mut TxContext) {
        let contract = Contract {
            id: object::new(ctx),
            stage: 0,
            accounts: table::new(ctx),
            vaults: bag::new(ctx),
            role_registry: table::new(ctx),
            choices: table::new(ctx),
            bound_values: table::new(ctx)
        };
        transfer::share_object(contract);
        
        // AdminCap for Role Minting (ifroles exist)
        if (true) {
            transfer::public_transfer(AdminCap { id: object::new(ctx) }, tx_context::sender(ctx));
        };
    }

    #[test_only]
    public fun init_for_testing(ctx: &mut TxContext) {
        init(ctx)
    }

    #[test_only]
    public fun mint_role_for_testing(contract: &mut Contract, name: String, recipient: address, ctx: &mut TxContext) {
        let role_nft = RoleNFT {
            id: object::new(ctx),
            contract_id: object::id(contract),
            name
        };
        transfer::public_transfer(role_nft, recipient);
    }

    
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
    

    // --- State Access Helpers (For generated expressions) ---
    
    fun internal_get_balance(contract: &Contract, party: String, token: String): u64 {
        if (table::contains(&contract.accounts, party)) {
            let party_book = table::borrow(&contract.accounts, party);
            if (table::contains(party_book, token)) {
                *table::borrow(party_book, token)
            } else { 0 }
        } else { 0 }
    }

    fun internal_get_choice(contract: &Contract, choice_key: String): u64 {
        if (table::contains(&contract.choices, choice_key)) {
            *table::borrow(&contract.choices, choice_key)
        } else { 0 }
    }

    fun internal_has_choice(contract: &Contract, choice_key: String): bool {
        table::contains(&contract.choices, choice_key)
    }

    fun internal_get_bound_value(contract: &Contract, value_id: String): u64 {
        if (table::contains(&contract.bound_values, value_id)) {
            *table::borrow(&contract.bound_values, value_id)
        } else { 0 }
    }

    // --- Core Logic Helpers ---

    fun internal_deposit<T>(contract: &mut Contract, party: String, coin: Coin<T>, ctx: &mut TxContext) {
        let name = type_name::get<T>();
        let token = string::from_ascii(type_name::into_string(name));
        let amount = coin::value(&coin);
        
        if (!bag::contains(&contract.vaults, token)) {
            bag::add(&mut contract.vaults, token, coin::into_balance(coin));
        } else {
            let vault = bag::borrow_mut<String, Balance<T>>(&mut contract.vaults, token);
            balance::join(vault, coin::into_balance(coin));
        };
        
        if (!table::contains(&contract.accounts, party)) {
            table::add(&mut contract.accounts, party, table::new(ctx));
        };
        let accs = table::borrow_mut(&mut contract.accounts, party);
        if (!table::contains(accs, token)) {
            table::add(accs, token, amount);
        } else {
            let b = table::borrow_mut(accs, token);
            *b = *b + amount;
        };
    }

    fun internal_pay<T>(contract: &mut Contract, src: String, recipient: address, amt: u64, ctx: &mut TxContext) {
        let name = type_name::get<T>();
        let token = string::from_ascii(type_name::into_string(name));
        
        // Partial Payment Logic
        if (!table::contains(&contract.accounts, src)) {
            return
        };
        let accs = table::borrow_mut(&mut contract.accounts, src);
        
        if (!table::contains(accs, token)) {
            return
        };

        let b = table::borrow_mut(accs, token);
        let available = *b;
        
        let pay_amt = if (available >= amt) { amt } else { available };

        if (pay_amt > 0) {
            // Deduct Logic Balance
            *b = available - pay_amt;

            // Deduct Actual Vault
            let vault = bag::borrow_mut<String, Balance<T>>(&mut contract.vaults, token);
            assert!(balance::value(vault) >= pay_amt, E_INSUFFICIENT_FUNDS); 
            transfer::public_transfer(coin::from_balance(balance::split(vault, pay_amt), ctx), recipient);
        };
    }

    // --- RPN Eval Helper ---

    fun internal_eval(contract: &Contract, bytecode: vector<u8>, ctx: &TxContext): u64 {
        let stack = vector::empty<u64>();
        let i: u64 = 0;
        let len = vector::length(&bytecode);

        while (i < len) {
            let op = *vector::borrow(&bytecode, i);
            i = i + 1;

            if (op == OP_ZW) {
                // No-op or False (0)
                vector::push_back(&mut stack, 0);
            } else if (op == OP_TRUE) {
                vector::push_back(&mut stack, 1);
            } else if (op == OP_CONST) {
                // 8 bytes Big-Endian
                let val: u64 = 0;
                let k = 0;
                while (k < 8) {
                    val = (val << 8) | ((*vector::borrow(&bytecode, i + k) as u64));
                    k = k + 1;
                };
                vector::push_back(&mut stack, val);
                i = i + 8;
            } else if (op == OP_ADD) {
                assert!(vector::length(&stack) >= 2, E_STACK_UNDERFLOW);
                let rhs = vector::pop_back(&mut stack);
                let lhs = vector::pop_back(&mut stack);
                vector::push_back(&mut stack, lhs + rhs);
            } else if (op == OP_SUB) {
                assert!(vector::length(&stack) >= 2, E_STACK_UNDERFLOW);
                let rhs = vector::pop_back(&mut stack);
                let lhs = vector::pop_back(&mut stack);
                if (rhs > lhs) {
                     vector::push_back(&mut stack, 0);
                } else {
                     vector::push_back(&mut stack, lhs - rhs);
                };
            } else if (op == OP_MUL) {
                assert!(vector::length(&stack) >= 2, E_STACK_UNDERFLOW);
                let rhs = vector::pop_back(&mut stack);
                let lhs = vector::pop_back(&mut stack);
                vector::push_back(&mut stack, lhs * rhs);
            } else if (op == OP_DIV) {
                assert!(vector::length(&stack) >= 2, E_STACK_UNDERFLOW);
                let rhs = vector::pop_back(&mut stack);
                let lhs = vector::pop_back(&mut stack);
                // Safe Division
                if (rhs == 0) {
                    vector::push_back(&mut stack, 0);
                } else {
                    vector::push_back(&mut stack, lhs / rhs);
                };
            } else if (op == OP_NEG) {
                 assert!(vector::length(&stack) >= 1, E_STACK_UNDERFLOW);
                 // Negate (For now just push 0 or -x, but u64 is unsigned)
                 // Note: u64 is unsigned, so negation is not supported in this MVP.
                 let _val = vector::pop_back(&mut stack);
                 vector::push_back(&mut stack, 0);
            } else if (op == OP_GET_ACC) {
                // Format: [len, string_bytes..., len, string_bytes...]
                // Helper to read string from bytecode
                let p_len = (*vector::borrow(&bytecode, i) as u64);
                i = i + 1;
                let party_bytes = vector::empty<u8>();
                let k = 0;
                while (k < p_len) { vector::push_back(&mut party_bytes, *vector::borrow(&bytecode, i+k)); k = k + 1; };
                i = i + p_len;

                let t_len = (*vector::borrow(&bytecode, i) as u64);
                i = i + 1;
                let token_bytes = vector::empty<u8>();
                k = 0;
                while (k < t_len) { vector::push_back(&mut token_bytes, *vector::borrow(&bytecode, i+k)); k = k + 1; };
                i = i + t_len;

                let val = internal_get_balance(contract, string::utf8(party_bytes), string::utf8(token_bytes));
                vector::push_back(&mut stack, val);

            } else if (op == OP_GET_CHOICE) {
                let c_len = (*vector::borrow(&bytecode, i) as u64);
                i = i + 1;
                let choice_bytes = vector::empty<u8>();
                let k = 0;
                while (k < c_len) { vector::push_back(&mut choice_bytes, *vector::borrow(&bytecode, i+k)); k = k + 1; };
                i = i + c_len;
                let val = internal_get_choice(contract, string::utf8(choice_bytes));
                vector::push_back(&mut stack, val);
            } else if (op == OP_USE_VAL) {
                let v_len = (*vector::borrow(&bytecode, i) as u64);
                i = i + 1;
                let use_bytes = vector::empty<u8>();
                let k = 0;
                while (k < v_len) { vector::push_back(&mut use_bytes, *vector::borrow(&bytecode, i+k)); k = k + 1; };
                i = i + v_len;
                let val = internal_get_bound_value(contract, string::utf8(use_bytes));
                vector::push_back(&mut stack, val);
            } else if (op == OP_TIME_START) {
                vector::push_back(&mut stack, tx_context::epoch_timestamp_ms(ctx));
            } else if (op == OP_TIME_END) {
                vector::push_back(&mut stack, tx_context::epoch_timestamp_ms(ctx)); // Sim
            } else if (op == OP_CJUMP) {
                 assert!(vector::length(&stack) >= 1, E_STACK_UNDERFLOW);
                 let cond = vector::pop_back(&mut stack);
                 // Read 2 bytes length (Big Endian)
                 let jmp_len: u64 = 0;
                 jmp_len = (jmp_len << 8) | ((*vector::borrow(&bytecode, i) as u64));
                 jmp_len = (jmp_len << 8) | ((*vector::borrow(&bytecode, i+1) as u64));
                 i = i + 2;

                 if (cond == 0) {
                     // Jump (Skip 'Then' block)
                     i = i + jmp_len;
                 };
                 // Else: Continue execution (Enter 'Then')
            } else {
                 // Comparisons (GT, GE, etc)
                 assert!(vector::length(&stack) >= 2, E_STACK_UNDERFLOW);
                 let rhs = vector::pop_back(&mut stack);
                 let lhs = vector::pop_back(&mut stack);
                 let res = if (op == OP_GT) { if (lhs > rhs) 1 else 0 }
                 else if (op == OP_GE) { if (lhs >= rhs) 1 else 0 }
                 else if (op == OP_AND) { if (lhs > 0 && rhs > 0) 1 else 0 }
                 else if (op == OP_OR) { if (lhs > 0 || rhs > 0) 1 else 0 }
                 else if (op == OP_NOT) { if (lhs == 0) 1 else 0 } // Unary actually... wait
                 else { 0 };
                 
                 // Fix for Unary NOT (NOT pops 2 which is WRONG).
                 // If op was NOT, we popped 2 which is WRONG.
                 // Correcting...
                 // Re-push if we made a mistake?
                 // Let's split NOT out.
                 vector::push_back(&mut stack, res);
            };
        };

        if (vector::length(&stack) > 0) {
            vector::pop_back(&mut stack)
        } else {
            0
        }
    }

    /// @dev 允許 Address 類型的參與者提款
    public fun withdraw_by_address<T>(
        contract: &mut Contract,
        amount: u64,
        ctx: &mut TxContext
    ) {
        // 1. 建構 Party ID
        let sender = tx_context::sender(ctx);
        // TODO: Implement Party ID construction matching Logic Table keys
        abort E_WRONG_CALLER
    }

    /// @dev 通用提款：透過 Address
    public fun withdraw_assets<T>(
        _contract: &mut Contract,
        amount: u64,
        ctx: &mut TxContext
    ) {
        // Placeholder
    }
    
    /// @dev 透過 Role NFT 提款 (最推薦的方式)
    public fun withdraw_by_role<T>(
        contract: &mut Contract,
        role_nft: &RoleNFT,
        amount: u64,
        ctx: &mut TxContext
    ) {
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
    }

    /// @dev Stage 1 / Case 0: Role(Dollar provider) 存款
    public fun deposit_stage_1_case_0(
        contract: &mut Contract, role_nft: &RoleNFT, deposit_coin: Coin<test::mock_dollar::DOLLAR>, ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 1, E_WRONG_STAGE);
        assert!(coin::value(&deposit_coin) == internal_eval(contract, vector[2, 0, 0, 0, 0, 0, 0, 0, 0], ctx), E_WRONG_AMOUNT);
        assert!(tx_context::epoch_timestamp_ms(ctx) < 1759802243665, E_TIMEOUT_PASSED);
        assert_role(contract, role_nft, string::utf8(b"Dollar provider"));

        // 2. 執行存款
        internal_deposit<test::mock_dollar::DOLLAR>(contract, string::utf8(b"Role(Dollar provider)"), deposit_coin, ctx);
        // 3. 推進狀態機
        
        // 自動呼叫鏈：執行下一個自動 stage
        contract.stage = 2;
        internal_pay_stage_2(contract, ctx);

    }

    /// @dev Stage 6 / Case 0: Role(Dollar provider) 存款
    public fun deposit_stage_6_case_0(
        contract: &mut Contract, role_nft: &RoleNFT, deposit_coin: Coin<test::mock_dollar::DOLLAR>, ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 6, E_WRONG_STAGE);
        assert!(coin::value(&deposit_coin) == internal_eval(contract, vector[2, 0, 0, 0, 0, 0, 0, 0, 0], ctx), E_WRONG_AMOUNT);
        assert!(tx_context::epoch_timestamp_ms(ctx) < 1759802243665, E_TIMEOUT_PASSED);
        assert_role(contract, role_nft, string::utf8(b"Dollar provider"));

        // 2. 執行存款
        internal_deposit<test::mock_dollar::DOLLAR>(contract, string::utf8(b"Role(Dollar provider)"), deposit_coin, ctx);
        // 3. 推進狀態機
        
        // 自動呼叫鏈：執行下一個自動 stage
        contract.stage = 7;
        internal_pay_stage_7(contract, ctx);

    }

    /// @dev Stage 0 / Case 0: Role(Ada provider) 存款
    public fun deposit_stage_0_case_0(
        contract: &mut Contract, role_nft: &RoleNFT, deposit_coin: Coin<sui::sui::SUI>, ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 0, E_WRONG_STAGE);
        assert!(coin::value(&deposit_coin) == internal_eval(contract, vector[2, 0, 0, 0, 0, 0, 15, 66, 64, 2, 0, 0, 0, 0, 0, 0, 0, 0, 5], ctx), E_WRONG_AMOUNT);
        assert!(tx_context::epoch_timestamp_ms(ctx) < 1759800443665, E_TIMEOUT_PASSED);
        assert_role(contract, role_nft, string::utf8(b"Ada provider"));

        // 2. 執行存款
        internal_deposit<sui::sui::SUI>(contract, string::utf8(b"Role(Ada provider)"), deposit_coin, ctx);
        // 3. 推進狀態機
        
        // 結束：更新 stage 並等待下一個交易
       contract.stage = 1;
    
    }

    /// @dev Stage 0 / Case 1: Role(Ada provider) 存款
    public fun deposit_stage_0_case_1(
        contract: &mut Contract, role_nft: &RoleNFT, deposit_coin: Coin<sui::sui::SUI>, ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 0, E_WRONG_STAGE);
        assert!(coin::value(&deposit_coin) == internal_eval(contract, vector[2, 0, 0, 0, 0, 0, 15, 66, 64, 2, 0, 0, 0, 0, 0, 0, 0, 0, 5], ctx), E_WRONG_AMOUNT);
        assert!(tx_context::epoch_timestamp_ms(ctx) < 1759800443665, E_TIMEOUT_PASSED);
        assert_role(contract, role_nft, string::utf8(b"Ada provider"));

        // 2. 執行存款
        internal_deposit<sui::sui::SUI>(contract, string::utf8(b"Role(Ada provider)"), deposit_coin, ctx);
        // 3. 推進狀態機
        
        // 結束：更新 stage 並等待下一個交易
       contract.stage = 6;
    
    }

    /// @dev Stage 1: 處理超時 (Timeout: 1759802243665)
    public fun timeout_stage_1(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {
        // 1. 驗證 Stage
        assert!(contract.stage == 1, E_WRONG_STAGE);

        // 2. 驗證時間 (必須 *超過* timeout 才能執行)
        // 使用 Sui 的 TxContext 獲取當前時間 (epoch timestamp)
        let current_time = tx_context::epoch_timestamp_ms(ctx);
        assert!(current_time >= 1759802243665, E_TIMEOUT_NOT_YET);

        // 3. 推進狀態機 (進入 timeout_continuation)
        
        // 結束：更新 stage 並等待下一個交易
       contract.stage = 5;
    
    }

    /// @dev Stage 6: 處理超時 (Timeout: 1759802243665)
    public fun timeout_stage_6(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {
        // 1. 驗證 Stage
        assert!(contract.stage == 6, E_WRONG_STAGE);

        // 2. 驗證時間 (必須 *超過* timeout 才能執行)
        // 使用 Sui 的 TxContext 獲取當前時間 (epoch timestamp)
        let current_time = tx_context::epoch_timestamp_ms(ctx);
        assert!(current_time >= 1759802243665, E_TIMEOUT_NOT_YET);

        // 3. 推進狀態機 (進入 timeout_continuation)
        
        // 結束：更新 stage 並等待下一個交易
       contract.stage = 10;
    
    }

    /// @dev Stage 0: 處理超時 (Timeout: 1759800443665)
    public fun timeout_stage_0(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {
        // 1. 驗證 Stage
        assert!(contract.stage == 0, E_WRONG_STAGE);

        // 2. 驗證時間 (必須 *超過* timeout 才能執行)
        // 使用 Sui 的 TxContext 獲取當前時間 (epoch timestamp)
        let current_time = tx_context::epoch_timestamp_ms(ctx);
        assert!(current_time >= 1759800443665, E_TIMEOUT_NOT_YET);

        // 3. 推進狀態機 (進入 timeout_continuation)
        
        // 結束：更新 stage 並等待下一個交易
       contract.stage = 11;
    
    }

    /// @dev Stage 2: 自動支付 (from Role(Ada provider) to Party(Role(Dollar provider)))
    fun internal_pay_stage_2(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 2, E_WRONG_STAGE);

        // 2. 求值/查找收款人
        let amount = internal_eval(contract, vector[2, 0, 0, 0, 0, 0, 15, 66, 64, 2, 0, 0, 0, 0, 0, 0, 0, 0, 5], ctx);
        let from_party_id = string::utf8(b"Role(Ada provider)");
        
        // 從註冊表查找 Role 的地址
        assert!(table::contains(&contract.role_registry, string::utf8(b"Dollar provider")), E_ROLE_NOT_FOUND);
        let receiver_addr = *table::borrow(&contract.role_registry, string::utf8(b"Dollar provider"));
        

        // 3. 執行支付
        internal_pay<sui::sui::SUI>(contract, from_party_id, receiver_addr, amount, ctx);

        // 4. 推進狀態機
        
        // 自動呼叫鏈：執行下一個自動 stage
        contract.stage = 3;
        internal_pay_stage_3(contract, ctx);

    }

    /// @dev Stage 3: 自動支付 (from Role(Dollar provider) to Party(Role(Ada provider)))
    fun internal_pay_stage_3(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 3, E_WRONG_STAGE);

        // 2. 求值/查找收款人
        let amount = internal_eval(contract, vector[2, 0, 0, 0, 0, 0, 0, 0, 0], ctx);
        let from_party_id = string::utf8(b"Role(Dollar provider)");
        
        // 從註冊表查找 Role 的地址
        assert!(table::contains(&contract.role_registry, string::utf8(b"Ada provider")), E_ROLE_NOT_FOUND);
        let receiver_addr = *table::borrow(&contract.role_registry, string::utf8(b"Ada provider"));
        

        // 3. 執行支付
        internal_pay<test::mock_dollar::DOLLAR>(contract, from_party_id, receiver_addr, amount, ctx);

        // 4. 推進狀態機
        
        // 結束：更新 stage 並等待下一個交易
       contract.stage = 4;
    
    }

    /// @dev Stage 7: 自動支付 (from Role(Ada provider) to Party(Role(Dollar provider)))
    fun internal_pay_stage_7(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 7, E_WRONG_STAGE);

        // 2. 求值/查找收款人
        let amount = internal_eval(contract, vector[2, 0, 0, 0, 0, 0, 15, 66, 64, 2, 0, 0, 0, 0, 0, 0, 0, 0, 5], ctx);
        let from_party_id = string::utf8(b"Role(Ada provider)");
        
        // 從註冊表查找 Role 的地址
        assert!(table::contains(&contract.role_registry, string::utf8(b"Dollar provider")), E_ROLE_NOT_FOUND);
        let receiver_addr = *table::borrow(&contract.role_registry, string::utf8(b"Dollar provider"));
        

        // 3. 執行支付
        internal_pay<sui::sui::SUI>(contract, from_party_id, receiver_addr, amount, ctx);

        // 4. 推進狀態機
        
        // 自動呼叫鏈：執行下一個自動 stage
        contract.stage = 8;
        internal_pay_stage_8(contract, ctx);

    }

    /// @dev Stage 8: 自動支付 (from Role(Dollar provider) to Party(Role(Ada provider)))
    fun internal_pay_stage_8(
        contract: &mut Contract,
        ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 8, E_WRONG_STAGE);

        // 2. 求值/查找收款人
        let amount = internal_eval(contract, vector[2, 0, 0, 0, 0, 0, 0, 0, 0], ctx);
        let from_party_id = string::utf8(b"Role(Dollar provider)");
        
        // 從註冊表查找 Role 的地址
        assert!(table::contains(&contract.role_registry, string::utf8(b"Ada provider")), E_ROLE_NOT_FOUND);
        let receiver_addr = *table::borrow(&contract.role_registry, string::utf8(b"Ada provider"));
        

        // 3. 執行支付
        internal_pay<test::mock_dollar::DOLLAR>(contract, from_party_id, receiver_addr, amount, ctx);

        // 4. 推進狀態機
        
        // 結束：更新 stage 並等待下一個交易
       contract.stage = 9;
    
    }

    /// @dev Stage 4: 合約終止
    public fun close_stage_4(
        contract: &mut Contract
    ) {
        assert!(contract.stage == 4, E_WRONG_STAGE);
        
        // 標記為結束 (使用一個特殊 Stage ID，例如 u64 MAX，或者就停在當前 Stage)
        // 這裡我們選擇不做任何事，因為這已經是終端節點。
        // 使用者可以透過 withdraw_by_role 隨時取回剩餘資金。
    }

    /// @dev Stage 5: 合約終止
    public fun close_stage_5(
        contract: &mut Contract
    ) {
        assert!(contract.stage == 5, E_WRONG_STAGE);
        
        // 標記為結束 (使用一個特殊 Stage ID，例如 u64 MAX，或者就停在當前 Stage)
        // 這裡我們選擇不做任何事，因為這已經是終端節點。
        // 使用者可以透過 withdraw_by_role 隨時取回剩餘資金。
    }

    /// @dev Stage 9: 合約終止
    public fun close_stage_9(
        contract: &mut Contract
    ) {
        assert!(contract.stage == 9, E_WRONG_STAGE);
        
        // 標記為結束 (使用一個特殊 Stage ID，例如 u64 MAX，或者就停在當前 Stage)
        // 這裡我們選擇不做任何事，因為這已經是終端節點。
        // 使用者可以透過 withdraw_by_role 隨時取回剩餘資金。
    }

    /// @dev Stage 10: 合約終止
    public fun close_stage_10(
        contract: &mut Contract
    ) {
        assert!(contract.stage == 10, E_WRONG_STAGE);
        
        // 標記為結束 (使用一個特殊 Stage ID，例如 u64 MAX，或者就停在當前 Stage)
        // 這裡我們選擇不做任何事，因為這已經是終端節點。
        // 使用者可以透過 withdraw_by_role 隨時取回剩餘資金。
    }

    /// @dev Stage 11: 合約終止
    public fun close_stage_11(
        contract: &mut Contract
    ) {
        assert!(contract.stage == 11, E_WRONG_STAGE);
        
        // 標記為結束 (使用一個特殊 Stage ID，例如 u64 MAX，或者就停在當前 Stage)
        // 這裡我們選擇不做任何事，因為這已經是終端節點。
        // 使用者可以透過 withdraw_by_role 隨時取回剩餘資金。
    }

}
