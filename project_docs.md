# Project Documentation & Architecture

## 1. Architecture Overview

The goal of this project is to compile financial contracts written in **Marlowe (JSON format)** into executable **Sui Move Smart Contracts** and corresponding **TypeScript SDKs**.

### System Flow
```mermaid
graph TD
    User[User] -->|Define| Spec[Marlowe JSON Spec]
    Spec -->|Input| Build[build.py]
    
    subgraph Generator
        Build --> Parser[parser.py]
        Parser -->|AST| FSM[fsm_model.py]
        FSM -->|Stages & Token Map| MoveGen[move_generator.py]
        FSM -->|Stages| TSGen[ts_generator.py]
    end
    
    MoveGen -->|Generate| Contract[Move Contract .move]
    MoveGen -->|Generate| Test[Move Tests .move]
    TSGen -->|Generate| SDK[TypeScript SDK .ts]
    
    subgraph Testing
        GenMocks[gen_mocks.py] -->|Generates| Mocks[mocks.move (Fake Coins)]
        Contract -->|Tested By| Suite[Sui Move Test Suite]
        Test -->|Runs In| Suite
        Mocks -->|Used By| Suite
    end
```

---

## 2. Testing Flow

To test the generated contracts locally, we use a 3-step process.

### Step 1: Generate Mock Tokens (Optional)
We need "fake" coins (like Mock USD, Mock ETH) to test trading logic without real assets.
```bash
python3 generator/gen_mocks.py
```
*Output: `contract/sources/mocks.move`*

### Step 2: Build Artifacts
Run the builder to convert all JSON specs in `specs/` into Move code and TS SDKs.
```bash
python3 generator/build.py
```
*Output: `contract/sources/*.move`, `contract/tests/*.move`, `sdk/*.ts`*

### Step 3: Run Move Tests
Use the standard Sui CLI to run the generated test suite.
```bash
cd contract
sui move test
```
*Expected Output: `Pass` for all tests.*

---

## 3. Implementation Details

Here is the breakdown of how each component works, its core idea, and the process flow.

### A. `generator/build.py` (The Orchestrator)
*   **Idea**: A clean entry point for production builds. It orchestrates the entire pipeline.
*   **Process**:
    1.  Scans `specs/` directory for `.json` files.
    2.  Reads JSON and passes it to the `parser`.
    3.  Passes AST to `fsm_model` to get Stage Infos.
    4.  Passes Stage Infos to `move_generator` (for contract & tests) and `ts_generator` (for SDK).
    5.  Writes file outputs to `contract/` and `sdk/`.
*   **Refactor Note**: We separated this from `gen_mocks.py` to keep production builds clean (no fake coins in production).

### B. `generator/parser.py` (The Reader)
*   **Idea**: Convert untyped JSON data into strongly-typed Python objects (AST).
*   **Process**:
    *   Uses recursive functions (`parse_contract`, `parse_action`, `parse_value`) to traverse the JSON tree.
    *   Maps Marlowe keywords (e.g., `when`, `then`, `let`, `pay`) to Python Data Classes.
*   **Flow**: `JSON Dict` $\to$ `Contract Class Instance` (Recursive AST).

### C. `generator/fsm_model.py` (The Planner)
*   **Idea**: Smart Contracts cannot easily handle deep recursion stack depth. We must "flatten" the recursive AST into a Linear **Finite State Machine (FSM)**.
*   **Process**:
    *   Assigns a unique integer `stage_id` to every node in the AST.
    *   Classifies nodes into types:
        *   **Interactive**: `Deposit`, `Choice`, `Notify` (Requires user tx).
        *   **Automatic**: `pay`, `if`, `let` (Contract auto-executes these).
    *   **Token Mapping**: Converts generic Marlowe tokens (e.g., "dollar") into specific Sui Move types (e.g., `test::mock_dollar::DOLLAR`) using a mapping table.
*   **Flow**: `Recursive AST` $\to$ `Dict[StageID, StageInfo]`.

### D. `generator/move_generator.py` (The Engineer)
*   **Idea**: Turn the abstract FSM stages into unsafe executable Move Bytecode.
*   **Process**:
    1.  **State Storage**: Generates `struct Contract` with tables for Accounts, Choices, and Variables using `sui::table`.
    2.  **Logic Engine**: Implements an on-chain **RPN (Reverse Polish Notation) Calculator** to evaluate complex Marlowe observations (e.g., `(ValueA + ValueB) > 100`) dynamically on-chain.
    3.  **Function Generation**:
        *   For each "Interactive" stage (e.g., waiting for deposit), it generates a public entry function: `public fun deposit_stage_X(...)`.
        *   Validates inputs (Amount, Token, Sender).
        *   Updates `contract.stage` to the next stage.
    4.  **Automation**: If the next stage is automatic (e.g., `If`), it recursively calls internal functions until it hits a stopping point (Result: One transaction can advance multiple stages).
*   **Flow**: `Stage Info` $\to$ `Move Source Code (.move)`.

### E. `generator/ts_generator.py` (The Bridge)
*   **Idea**: Developers shouldn't need to craft raw Move transactions. The SDK provides a typed interface.
*   **Process**:
    *   Iterates through the same `StageInfo` map.
    *   For every public Move function generated, it creates a corresponding TypeScript method.
    *   **Abstraction**: Hides `tx.moveCall`, BCS serialization, and Type Tag handling from the end user.
*   **Flow**: `Stage Info` $\to$ `MarloweContract` class (TypeScript).
