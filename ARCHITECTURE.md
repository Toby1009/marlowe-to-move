# Marlowe on Sui: Architecture Documentation

## Overview
This project provides a complete toolchain for deploying **Marlowe financial contracts** onto the **Sui Blockchain**. It translates Marlowe's domain-specific language (JSON DSL) into a highly efficient, verified **Sui Move Smart Contract** and a matching **TypeScript SDK**.

## 🏗️ System Architecture

### 1. The Compilation Pipeline
The system follows a 4-step generation process:
1.  **Parsing**: Reads `specs/*.json` (Marlowe DSL) and converts it into a Python AST (`parser.py`).
2.  **Linearization**: Flattens the recursive AST into a Linear State Machine (`fsm_model.py`).
    -   Each node becomes a "Stage".
    -   Recursive logic (If/Else) is compiled into Jump operations or separate Stages.
3.  **Code Generation**:
    -   **Move**: `move_generator.py` produces the smart contract (`sources/`).
    -   **TypeScript**: `ts_generator.py` produces the client SDK (`sdk/`).
4.  **Deployment**: `deploy.py` handles compiling and publishing to the Sui network.

*   **Multi-Token Vault (Bag)**: The contract uses a `Bag` to store heterogeneous assets (`Balance<T>`).
    -   Users can deposit ANY Coin type defined in the contract.
    -   Internal accounting tracks "logical" balances vs "actual" vault balances.

### 3. Deployment Flow
Deployment is handled by `generator/deploy.py`, which automates the transition from Move code to a live contract:
1.  **Publish**: Runs `sui client publish` and captures JSON output.
2.  **Artifact Tracking**: Extracts `package_id` and `contract_id`, saving them to `deployments/deployment.json`.
3.  **SDK Synchronization**: Automatically triggers `build.py` after deployment. This ensures that the generated TypeScript SDKs are instantly updated with the new on-chain addresses.
4.  **Network Awareness**: Currently configured for `testnet` (default Sui CLI environment).

### 3. File Structure
```text
.
├── generator/              # Python Generators & Utilities (Was `scripts`)
│   ├── build.py            # Main Entry (Production)
│   ├── gen_mocks.py        # Mock Token Generator (Testing)
│   ├── move_generator.py   # Code Logic
│   └── ...
├── contract/               # Sui Move Package
│   ├── Move.toml
│   ├── sources/            # Generated Move Code
│   └── tests/
├── sdk/                    # TypeScript Client SDK
│   ├── contract_sdk.ts
│   ├── package.json
│   └── tsconfig.json
├── specs/                  # Marlowe Contract Inputs (JSON)
├── deployments/            # Deployment Artifacts
```

## 🚀 Usage Guide

### Prerequisites
-   Python 3.10+
-   Sui Client CLI
-   Node.js & NPM

### Step 1: Generate
Compile all specs in `specs/`:
```bash
python3 generator/build.py
```
(Optional) Generate mock tokens for local testing:
```bash
python3 generator/gen_mocks.py
```

### Step 2: Test (Local)
Run Move tests inside the `contract` folder:
```bash
cd contract
sui move test
cd ..
```

### Step 3: Deploy (Testnet/Mainnet)
Use the python deploy script (handles pathing automatically):
```bash
python3 generator/deploy.py
```

### Step 4: Interact (Frontend)
Use the generated SDK to build your UI or bot.
```typescript
import { MarloweContract } from './sdk/contract_sdk';
// Methods are strongly typed based on your contract stages!
const contract = new MarloweContract();
contract.choice_Stage0_0_pick_number(tx, roleNftId, 5);
```
