
import { Transaction } from '@mysten/sui/transactions';
import { bcs } from '@mysten/sui/bcs';

export const PACKAGE_ID = "0xae0264e41707bd896bcc6d3f9252635d7d53b6bed4bcc979a315d004ecb4138b";
export const CONTRACT_ID = "0xc44a63a0c12d410e4c75c8b39f7f8413f83d851bfb3c77a6718b72bf724206da";

export class MarloweContract {
    packageId: string;
    contractId: string;
    moduleId: string = "simple_voting_marlowe";

    constructor(packageId: string = PACKAGE_ID, contractId: string = CONTRACT_ID) {
        this.packageId = packageId;
        this.contractId = contractId;
    }

    /**
     * Helper to call a Move function
     */
    private moveCall(tx: Transaction, func: string, args: any[], typeArgs: string[] = []) {
        tx.moveCall({
            target: `${this.packageId}::${this.moduleId}::${func}`,
            arguments: args,
            typeArguments: typeArgs,
        });
    }

    /**
     * Mint a Role NFT (Requires AdminCap)
     */
    mintRole(tx: Transaction, adminCap: string, name: string, recipient: string) {
        this.moveCall(tx, 'mint_role', [
            tx.object(adminCap),
            tx.object(this.contractId),
            tx.pure(bcs.string().serialize(name)),
            tx.pure(bcs.Address.serialize(recipient))
        ]);
    }

    /**
     * Withdraw Assets (via Role)
     * @param typeArg The Coin Type (e.g. '0x2::sui::SUI')
     */
    withdraw(tx: Transaction, roleNftId: string, amount: bigint, typeArg: string) {
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
    }

    /**
     * Stage 0: Choice 'vote_result' by Role 'Voter'
      * @param choiceVal Value between 0 and 1
     */
    choice_Stage0_0_vote_result(tx: Transaction, roleNftId: string, choiceVal: number | bigint) {
        this.moveCall(tx, 'choice_stage_0_case_0', [
            tx.object(this.contractId),
            tx.object(roleNftId),
            tx.pure(bcs.u64().serialize(choiceVal))
        ]);
    }

    /**
     * Stage 0: Timeout Action (Trigger when time >= 1775174399000)
     */
    timeout_Stage0(tx: Transaction) {
        this.moveCall(tx, 'timeout_stage_0', [
            tx.object(this.contractId)
        ]);
    }

    public getTimeouts(): Record<number, number> {
        return {"0": 1775174399000};
    }

}
