
module test::generated_marlowe {
    use sui::coin::{Self, Coin};
    use sui::table::{Self, Table};
    use sui::balance::{Self, Balance};
    use sui::object::{Self, ID, UID};
    use sui::transfer;
    use sui::tx_context::{Self, TxContext};
    use std::string::{Self, String};

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

    
    public struct RoleNFT has key, store {
        id: UID,
        contract_id: ID,
        name: String
    }
    

    public struct Contract has key {
        id: UID,
        stage: u64,
        accounts: Table<String, Table<String, u64>>,
        vaults: Table<String, Balance<sui::sui::SUI>>,
        role_registry: Table<String, address>,
        choices: Table<String, u64>,
        bound_values: Table<String, u64>
    }

    fun init(ctx: &mut TxContext) {
        let contract = Contract {
            id: object::new(ctx),
            stage: 0,
            accounts: table::new(ctx),
            vaults: table::new(ctx),
            role_registry: table::new(ctx),
            choices: table::new(ctx),
            bound_values: table::new(ctx)
        };
        transfer::share_object(contract);
    }

    
    fun assert_role(contract: &Contract, role_nft: &RoleNFT, expected_name: String) {
        assert!(role_nft.contract_id == object::id(contract), E_INVALID_ROLE_NFT);
        assert!(role_nft.name == expected_name, E_WRONG_ROLE);
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

    fun internal_deposit(contract: &mut Contract, party: String, coin: Coin<sui::sui::SUI>, ctx: &mut TxContext) {
        let token = string::utf8(b"SUI");
        let amount = coin::value(&coin);
        if (!table::contains(&contract.vaults, token)) {
            table::add(&mut contract.vaults, token, coin::into_balance(coin));
        } else {
            balance::join(table::borrow_mut(&mut contract.vaults, token), coin::into_balance(coin));
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

    fun internal_pay(contract: &mut Contract, src: String, recipient: address, amt: u64, ctx: &mut TxContext) {
        let token = string::utf8(b"SUI");
        assert!(table::contains(&contract.accounts, src), E_INSUFFICIENT_FUNDS);
        let accs = table::borrow_mut(&mut contract.accounts, src);
        assert!(table::contains(accs, token), E_INSUFFICIENT_FUNDS);
        let b = table::borrow_mut(accs, token);
        assert!(*b >= amt, E_INSUFFICIENT_FUNDS);
        *b = *b - amt;

        let vault = table::borrow_mut(&mut contract.vaults, token);
        assert!(balance::value(vault) >= amt, E_INSUFFICIENT_FUNDS);
        transfer::public_transfer(coin::from_balance(balance::split(vault, amt), ctx), recipient);
    }

    // --- Withdraw (Pull Pattern) Helpers ---

    /// @dev 允許 Address 類型的參與者提款
    public fun withdraw_by_address(
        contract: &mut Contract,
        token_name: String,
        amount: u64,
        ctx: &mut TxContext
    ) {
        // 1. 建構 Party ID
        let sender = tx_context::sender(ctx);
        let party_id_str = sui::address::to_string(sender); 
        let mut full_party_id = string::utf8(b"Address(");
        string::append(&mut full_party_id, party_id_str);
        string::append(&mut full_party_id, string::utf8(b")"));
        // 注意：這裡簡化處理。實際生成的 ID 可能是 "Address(0x...)"。
        // 建議：為了簡化，這裡我們暫時假設使用者知道自己的 Party ID String，
        // 或者我們在 Move 中需要更強的 Address -> String 轉換庫。
        // 為了現在能運作，我們先用一種更直接的方式：檢查 accounts。
        
        // 修正策略：直接讓使用者傳入 party_id_str，然後我們驗證 sender
        abort E_WRONG_CALLER // 暫時不實作複雜的 Address 字串轉換，推薦使用 withdraw_assets
    }

    /// @dev 通用提款：透過 Address
    public fun withdraw_assets(
        contract: &mut Contract,
        token_name: String,
        amount: u64,
        ctx: &mut TxContext
    ) {
        let sender = tx_context::sender(ctx);
        // 這裡需要一個可靠的方式將 Address 轉為當初存入時的 String Key
        // 由於 Move std::string 限制，這比較麻煩。
        // 替代方案：我們依賴 Role 提款，或假設使用者能提供正確的 Party ID (需驗證)。
    }
    
    /// @dev 透過 Role NFT 提款 (最推薦的方式)
    public fun withdraw_by_role(
        contract: &mut Contract,
        role_nft: &RoleNFT,
        token_name: String,
        amount: u64,
        ctx: &mut TxContext
    ) {
        // 1. 驗證 Role 歸屬
        assert!(role_nft.contract_id == object::id(contract), E_INVALID_ROLE_NFT);
        
        // 2. 建構 Party Key: "Role(Name)"
        let mut party_key = string::utf8(b"Role(");
        string::append(&mut party_key, role_nft.name);
        string::append(&mut party_key, string::utf8(b")"));

        // 3. 執行內部支付邏輯 (從合約轉給 Caller)
        let caller = tx_context::sender(ctx);
        internal_pay(contract, party_key, caller, amount, ctx);
    }

    /// @dev Stage 1 / Case 0: Role(Dollar provider) 存款
    public fun deposit_stage_1_case_0(
        contract: &mut Contract, role_nft: &RoleNFT, deposit_coin: Coin<sui::sui::SUI>, ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 1, E_WRONG_STAGE);        assert!(coin::value(&deposit_coin) == 0, E_WRONG_AMOUNT);        assert_role(contract, role_nft, string::utf8(b"Dollar provider"));

        // 2. 執行存款
        internal_deposit(contract, string::utf8(b"Role(Dollar provider)"), deposit_coin, ctx);
        // 3. 推進狀態機
        
        // 自動呼叫鏈：執行下一個自動 stage
        contract.stage = 2;
        internal_pay_stage_2(contract, ctx);

    }

    /// @dev Stage 6 / Case 0: Role(Dollar provider) 存款
    public fun deposit_stage_6_case_0(
        contract: &mut Contract, role_nft: &RoleNFT, deposit_coin: Coin<sui::sui::SUI>, ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 6, E_WRONG_STAGE);        assert!(coin::value(&deposit_coin) == 0, E_WRONG_AMOUNT);        assert_role(contract, role_nft, string::utf8(b"Dollar provider"));

        // 2. 執行存款
        internal_deposit(contract, string::utf8(b"Role(Dollar provider)"), deposit_coin, ctx);
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
        assert!(contract.stage == 0, E_WRONG_STAGE);        assert!(coin::value(&deposit_coin) == (1000000 * 0), E_WRONG_AMOUNT);        assert_role(contract, role_nft, string::utf8(b"Ada provider"));

        // 2. 執行存款
        internal_deposit(contract, string::utf8(b"Role(Ada provider)"), deposit_coin, ctx);
        // 3. 推進狀態機
        
        // 結束：更新 stage 並等待下一個交易
       contract.stage = 1;
    
    }

    /// @dev Stage 0 / Case 1: Role(Ada provider) 存款
    public fun deposit_stage_0_case_1(
        contract: &mut Contract, role_nft: &RoleNFT, deposit_coin: Coin<sui::sui::SUI>, ctx: &mut TxContext
    ) {
        // 1. 驗證
        assert!(contract.stage == 0, E_WRONG_STAGE);        assert!(coin::value(&deposit_coin) == (1000000 * 0), E_WRONG_AMOUNT);        assert_role(contract, role_nft, string::utf8(b"Ada provider"));

        // 2. 執行存款
        internal_deposit(contract, string::utf8(b"Role(Ada provider)"), deposit_coin, ctx);
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
        let amount = (1000000 * 0);
        let from_party_id = string::utf8(b"Role(Ada provider)");
        
        // 從註冊表查找 Role 的地址
        assert!(table::contains(&contract.role_registry, string::utf8(b"Dollar provider")), E_ROLE_NOT_FOUND);
        let receiver_addr = *table::borrow(&contract.role_registry, string::utf8(b"Dollar provider"));
        

        // 3. 執行支付
        internal_pay(contract, from_party_id, receiver_addr, amount, ctx);

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
        let amount = 0;
        let from_party_id = string::utf8(b"Role(Dollar provider)");
        
        // 從註冊表查找 Role 的地址
        assert!(table::contains(&contract.role_registry, string::utf8(b"Ada provider")), E_ROLE_NOT_FOUND);
        let receiver_addr = *table::borrow(&contract.role_registry, string::utf8(b"Ada provider"));
        

        // 3. 執行支付
        internal_pay(contract, from_party_id, receiver_addr, amount, ctx);

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
        let amount = (1000000 * 0);
        let from_party_id = string::utf8(b"Role(Ada provider)");
        
        // 從註冊表查找 Role 的地址
        assert!(table::contains(&contract.role_registry, string::utf8(b"Dollar provider")), E_ROLE_NOT_FOUND);
        let receiver_addr = *table::borrow(&contract.role_registry, string::utf8(b"Dollar provider"));
        

        // 3. 執行支付
        internal_pay(contract, from_party_id, receiver_addr, amount, ctx);

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
        let amount = 0;
        let from_party_id = string::utf8(b"Role(Dollar provider)");
        
        // 從註冊表查找 Role 的地址
        assert!(table::contains(&contract.role_registry, string::utf8(b"Ada provider")), E_ROLE_NOT_FOUND);
        let receiver_addr = *table::borrow(&contract.role_registry, string::utf8(b"Ada provider"));
        

        // 3. 執行支付
        internal_pay(contract, from_party_id, receiver_addr, amount, ctx);

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
