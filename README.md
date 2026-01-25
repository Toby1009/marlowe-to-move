# Marlowe to Sui Move Compiler 🌉

> **Run Marlowe Financial Contracts on Sui Blockchain**

This project provides a robust pipeline to compile **Marlowe** (Cardano's financial DSL) into **Sui Move** smart contracts. It enables the execution of complex financial agreements (Swap, Escrow, etc.) on the Sui network with a state-of-the-art architecture.

## ✨ Features

-   **Finite State Machine (FSM)**: Enforces strict contract stages derived from Marlowe semantics.
-   **RPN Interpreter**: Implements a Stack Machine in Move to evaluate logic, arithmetic, and observations at runtime (overcoming Move's lack of recursive structs).
-   **Role-Based Access**: `RoleNFT` implementation with `AdminCap` for secure minting and permissioned actions.
-   **Timeout Safety**: Automatic deadline enforcement with "Escape Hatch" state transitions (Plan A/B support).
-   **TypeScript SDK**: Auto-generated SDK (`contract_sdk.ts`) for seamless frontend integration.

## 📂 Project Structure

-   `generator/`: Python scripts to compile JSON specs -> Move & TS.
-   `contract/`: Valid Sui Move package (Sources & Tests).
-   `sdk/`: TypeScript client SDK.
-   `specs/`: Marlowe Contract Specifications (JSON).

## 🚀 Quick Start

### 1. Prerequisites
-   Python 3.10+
-   Sui Client CLI
-   Node.js & NPM

### 2. Generate Contract
Compile the `specs/swap_ada.json` (default) into Move code:
```bash
python3 generator/repro_generator.py
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
-   **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Detailed technical design (FSM, RPN, File Layout).
-   **[note.md](./note.md)**: Dev notes and implementation details.

## 🔗 Links
-   [Marlowe Lang](https://marlowe-finance.io/)
-   [Sui Move](https://docs.sui.io/)

