# Marlowe to Sui Move Compiler 🌉

> **Run Marlowe Financial Contracts on Sui Blockchain**

This project provides a robust pipeline to compile **Marlowe** (Cardano's financial DSL) into **Sui Move** smart contracts. It enables the execution of complex financial agreements (Swap, Escrow, etc.) on the Sui network with a state-of-the-art architecture.

## ✨ Features

-   **Finite State Machine (FSM)**: Enforces strict contract stages derived from Marlowe semantics.
-   **RPN Interpreter**: Implements a Stack Machine in Move to evaluate logic, arithmetic, and observations at runtime (overcoming Move's lack of recursive structs).
-   **Role-Based Access**: `RoleNFT` implementation with `AdminCap` for secure minting and permissioned actions.
-   **Timeout Safety**: Automatic deadline enforcement with "Escape Hatch" state transitions (Plan A/B support).
-   **TypeScript SDK**: Auto-generated SDK (`contract_sdk.ts`) for seamless frontend integration.
-   **BPMN Export**: Deterministic BPMN 2.0 XML, lane/pool layout, SVG rendering, and PNG export for supported Marlowe JSON specs.

## 📂 Project Structure

-   `generator/`: Build scripts (`build.py`, `gen_mocks.py`) and compiler logic.
-   `contract/`: Valid Sui Move package (Sources & Tests).
-   `sdk/`: TypeScript client SDK.
-   `specs/`: Marlowe Contract Specifications (JSON).
-   `artifacts/bpmn/`: Generated BPMN, SVG, and PNG diagram outputs.

## 🚀 Quick Start

### 1. Prerequisites
-   Python 3.10+
-   Sui Client CLI
-   Node.js & NPM

### 2. Generate Contract
Compile **all** specs in `specs/` (e.g. `swap_ada.json`, `swap_eth_usdc.json`) into Move code and TS SDKs:
```bash
python3 generator/build.py
```

Generate BPMN for a spec:
```bash
python3 generator/cli.py bpmn --spec simple_swap.dex_swap
```
This writes diagram artifacts under `artifacts/bpmn/` by default.

Generate BPMN + SVG + PNG and validate the output:
```bash
python3 generator/cli.py bpmn --spec simple_swap.dex_swap --svg --png --validate
python3 generator/cli.py validate-bpmn --spec simple_swap.dex_swap
```

### 3. (Optional) Generate Mocks
If you need "Fake Coins" (Mock USD, ETH, etc.) for local testing:
```bash
python3 generator/gen_mocks.py
```

### 3. Run Tests
Verify the generated contract logic locally:
```bash
cd contract
sui move test
```

### 4. Deploy
Publish to Sui Testnet/Mainnet:
```bash
python3 generator/deploy.py
```

## 📚 Documentation
-   **[project_docs.md](./project_docs.md)**: **(Recommended)** Complete Architecture, Testing Flow & Implementation Guide.
-   **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Technical design details.
-   **[BPMN_MAPPING.md](./BPMN_MAPPING.md)**: Marlowe JSON to BPMN mapping scope and rules.
-   **[note.md](./note.md)**: Additional dev notes.

## 🔗 Links
-   [Marlowe Lang](https://marlowe-finance.io/)
-   [Sui Move](https://docs.sui.io/)
