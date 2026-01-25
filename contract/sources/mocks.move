
module test::mock_dollar {
    use sui::coin;
    use sui::transfer;
    use sui::tx_context::{Self, TxContext};
    use std::option;
    struct DOLLAR has drop {}
    public entry fun mint(ctx: &mut TxContext) {
        let (treasury, metadata) = coin::create_currency(DOLLAR{}, 9, b"DOL", b"Mock Dollar", b"", option::none(), ctx);
        transfer::public_freeze_object(metadata);
        transfer::public_transfer(treasury, tx_context::sender(ctx));
    }
}
module test::mock_eth {
    use sui::coin;
    use sui::transfer;
    use sui::tx_context::{Self, TxContext};
    use std::option;
    struct ETH has drop {}
    public entry fun mint(ctx: &mut TxContext) {
        let (treasury, metadata) = coin::create_currency(ETH{}, 9, b"ETH", b"Mock ETH", b"", option::none(), ctx);
        transfer::public_freeze_object(metadata);
        transfer::public_transfer(treasury, tx_context::sender(ctx));
    }
}
module test::mock_usdc {
    use sui::coin;
    use sui::transfer;
    use sui::tx_context::{Self, TxContext};
    use std::option;
    struct USDC has drop {}
    public entry fun mint(ctx: &mut TxContext) {
        let (treasury, metadata) = coin::create_currency(USDC{}, 9, b"USDC", b"Mock USDC", b"", option::none(), ctx);
        transfer::public_freeze_object(metadata);
        transfer::public_transfer(treasury, tx_context::sender(ctx));
    }
}
