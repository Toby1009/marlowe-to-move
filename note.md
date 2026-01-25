# Project Note: Marlowe on Sui

## 📌 Project Overview
This project enables the deployment of Marlowe financial contracts on the Sui Blockchain. It creates a bridge between Marlowe's DSL (JSON) and Sui Move, utilizing a Python-based generator to produce:
1.  **Sui Move Contract**: A Finite State Machine (FSM) enforcing contract stages.
2.  **TypeScript SDK**: A typed client for interacting with the contract.

## 🏗️ Architecture
The project is structured into three main components:
-   **`generator/`**: Python scripts (`repro_generator.py`) that compile JSON specs into Move code.
-   **`contract/`**: The Sui Move package containing the generated logic (`sources/`) and tests (`tests/`).
-   **`sdk/`**: The generated TypeScript SDK for frontend integration.

## 💡 Key Implementations

### 1. RPN Interpreter (Stack Machine)
Since Move does not support recursive structs (needed for deep ASTs), we implemented a **Reverse Polish Notation (RPN)** interpreter.
-   Logic (Values/Observations) is compiled into a bytecode `vector<u8>`.
-   `internal_eval` executes this bytecode at runtime using a stack (`vector<u64>`).
-   Supports: Arithmetic (`ADD`, `SUB`, `MUL`, `DIV`), Logic (`AND`, `OR`, `NOT`), and State Access (`GET_ACC`, `GET_CHOICE`).

### 2. Finite State Machine (FSM)
-   The contract tracks a `stage` variable (`u64`).
-   Each Marlowe `When` clause becomes a specific Move function (e.g., `deposit_stage_0_case_0`).
-   Functions strictly assert `contract.stage == expected` to enforce the flow.

### 3. Role-Based Access Control
-   **RoleNFT**: Represents a participant role (e.g., "Dollar provider").
-   **AdminCap**: Required to mint roles (`mint_role`). This ensures secure production deployment.
-   **Registry**: The contract stores a mapping of Roles to Addresses for internal payouts.

### 4. Timeout Mechanism
-   **Deadline Checks**: Every action checks `now < timeout` to prevent late deposits.
-   **Escape Hatch**: Dedicated `timeout_stage_X` functions allow advancing the contract if a party is unresponsive after the deadline.
-   **Agent/Frontend**: The SDK provides `getTimeouts()` to help frontends trigger these escapes.

## ✅ Current Status (Swap Ada)
-   **Spec**: `specs/swap_ada.json`
-   **Features**:
    -   [x] Deposit Logic (ADA/SUI & Custom Tokens)
    -   [x] Mock Token Generation (for testing custom IDs)
    -   [x] Atomic Swap Flow via FSM
    -   [x] Timeout Handling
    -   [x] AdminCap & Minting
-   **Verification**:
    -   `sui move build` passes.
    -   Legacy/2024 Move compatibility handled.
    -   Linter warnings resolved.

## 🚀 Next Steps
1.  **Frontend Development**: Use the SDK to build a React/Next.js UI.
2.  **Mainnet Deployment**: Use `deploy.py` for actual deployment.
3.  **Agent Bot**: Implement a simple keeper script to trigger timeouts automatically.
