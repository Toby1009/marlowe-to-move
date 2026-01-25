
#[test_only]
module test::contract_tests {
    use sui::test_scenario;
    use sui::coin;
    use std::option;
    use test::complex_contract::{Self, Contract, RoleNFT};

    #[test]
    fun test_happy_path() {
        let admin = @0xA;
        let user = @0xB;
        
        let scenario_val = test_scenario::begin(admin);
        let scenario = &mut scenario_val;
        
        // 1. Initialize Contract
        {
            complex_contract::init_for_testing(test_scenario::ctx(scenario));
        };
        test_scenario::next_tx(scenario, admin);
        
        // 2. Verify Contract Exists
        {
            let contract = test_scenario::take_shared<Contract>(scenario);
            test_scenario::return_shared(contract);
        };
        test_scenario::next_tx(scenario, admin); // Admin turn done

        
        // Mint Role 'Oracle' to user
        {
            let contract = test_scenario::take_shared<Contract>(scenario);
            complex_contract::mint_role_for_testing(&mut contract, std::string::utf8(b"Oracle"), user, test_scenario::ctx(scenario));
            test_scenario::return_shared(contract);
        };
        test_scenario::next_tx(scenario, user);


        
        // Perform Choice 'pick_number'
        {
            let contract = test_scenario::take_shared<Contract>(scenario);
            let role_nft = test_scenario::take_from_sender<RoleNFT>(scenario);
            
            complex_contract::choice_stage_0_case_0(&mut contract, &role_nft, 1, test_scenario::ctx(scenario));
            
            test_scenario::return_to_sender(scenario, role_nft);
            test_scenario::return_shared(contract);
        };
        test_scenario::next_tx(scenario, user);


        // TODO: Mint Roles and interact with stages
        // Use test_scenario::take_shared<Contract>(scenario) to get contract
        // Call complex_contract::choice_... or deposit_...
        
        test_scenario::end(scenario_val);
    }
}
