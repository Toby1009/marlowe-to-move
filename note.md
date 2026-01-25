# Note

## 目前工作

Action= Deposit AccountId Party Token Value
|Choice ChoiceId Bound list
|Notify Observation

datatype Case= Case Action Contract
and Contract= Close
|Pay AccountId Payee Token Value Contract
|If Observation Contract Contract
|When Case list Timeout Contract
|Let ValueId Value Contract
|Assert Observation Contract

type-synonym AccountId = Party

datatype Party=
Address Address
|Role RoleName

> Party有Address/Role形式，而Address是Address，而Role是RoleName
其中Address是地址，而Role是指憑證，擁有憑證的都可以算

datatype Payee
= Account AccountId
|Party Party

function:

- 參數
- stage
- 該stage要的操作
- 下一個contract的參數

Contract function:

- stage: 一個 u64 或 String，用來標識當前的合約狀態（例如，WAITING_FOR_P1_DEPOSIT）。
- state: 一個 State 結構，對應 Marlowe 的 State ，包含內部帳戶、選擇和綁定值。
- participants: 用於儲存 Party 資訊的 Table。
- config: 儲存合約的靜態參數（如超時時間戳等）。

deposit_<stage>:
currency_symbol & token_name: 共同組成Token Type，只用空當SUI，要放在開頭當<SUI>或是其他
contract: 用來引入合約狀態
receiver: receiver不一定都是地址
deposit_coin: deposit_coin的type需要油currency_symbol & token_name決定
amount: deposit之數量

要判斷party是否是擁有某個權限或是某個地址
如果是address，要判斷是否呼叫者與該address襄公
如果是role，要先靠輸入判斷擁有權限，然後判斷是否跟role名稱相同，合約一開始會先分配好role。

初始化時先給白名單，後續透過白名單去分配role nft

Pay AccountId Payee Token Value Contract
pay_<stage>:
  contract: &mut Contract,
  accountId: address,
  receiver: address,
  pay_coin: &mut Coin<{token_name}>,
  amount: u64,

付款者要是內部帳戶，收款者可以是內部或外部
內部帳戶使用dynamic_field
先

fsm_model在做的時候是在做「合約藍圖」，資訊不應該在執行時傳遞，而是在程式碼生成時
問題: [是否紀律下個function參數](https://docs.google.com/document/d/1Io_yDkd3AACgqoEMAQGO0WN7R7Wa_w-eH2SScLW0y8E/edit?tab=t.0)

## 下一個工作

搞個MVP設計，實現Deposit

- Role如何連結？
  - 等到要參與時，透過一個 public entry fun mint_role(name: String, recipient: address) 來 mint 對應角色
- token如何知道是哪個token?在建立合約時用判斷的
  - currency_symbol:package_id
  - token_name:module::token_name
- Account(合約內部帳戶)：用來記錄參與者的內部帳戶，用來儲存資產與紀錄各自儲存在合約中的資產有多少
  - 記帳
  - vault

- Contract為owned_object，在合約初始化前定義好白名單，然後也要有增加白名單的function，合約初始化也包含mint role nft

還是我之後再做CLI時可以去先查什麼stage，然後再對應到該stage的function，這樣我就能透過像是deposit_x時先去對輸入參數做檢查，不用延遲檢查type

## 11/18

- 合約初始化白名單要搞，分發問題
-

1. 擴充 Move 中的 Contract 狀態
您目前的 Contract struct 只包含了 accounts、vaults 和 role_registry。根據 Marlowe 規範 §2.1.8 (State) ，您還需要儲存 choices 和 boundValues：

choices ：用於儲存 Choice action 的結果。

boundValues ：用於儲存 Let 語句的求值結果。

您需要將這兩者（可能是 Table）添加到 generated_contract.move 的 Contract struct 中，並在 init 函式中初始化它們。

2. 在 Move 中實作 internal_eval_value
您在程式碼中標記了 // TODO: 實作 internal_eval_value 。這需要一個（或一系列）Move 函式，它能接收 Marlowe Value 的表示法，並根據當前 Contract 狀態回傳一個 u64。

這需要能處理規範 §2.1.5  中定義的所有 Value 類型：

Constant ：直接回傳數值。

AddValue, SubValue, MulValue, DivValue ：遞迴呼叫求值器並執行算術運算。

AvailableMoney ：從 contract.accounts 讀取餘額（類似 internal_pay 中的邏輯 ）。

ChoiceValue ：從您在步驟 1 新增的 contract.choices 表中讀取值。

UseValue ：從您在步驟 1 新增的 contract.boundValues 表中讀取值。

TimeIntervalStart / TimeIntervalEnd ：從 TxContext 獲取當前交易的時間戳（Marlowe 規範 §2.1.8  提到了交易的有效時間）。

Cond ：需要呼叫 internal_eval_observation。

3. 在 Move 中實作 internal_eval_observation
同樣地，您需要實作 internal_eval_observation 函式 ，它能回傳一個 bool。這需要處理規範 §2.1.5  中定義的所有 Observation 類型：

TrueObs, FalseObs ：回傳布林值。

AndObs, OrObs, NotObs ：遞迴呼叫並執行邏輯運算。

ValueGE, ValueGT, ValueLT, ValueLE, ValueEQ ：呼叫 internal_eval_value 比較兩個 Value 的結果。

ChoseSomething ：檢查 contract.choices 表中是否存在某個 ChoiceId。

4. 實作缺失的 Action 和 Contract 產生器
在 move_generator.py (line 492, 494) 中，您標記了幾個 TODO。一旦您有了 internal_eval_value 和 internal_eval_observation，您就可以實作：

generate_choice_function (for Choice )：

這應該是一個 public fun（像 deposit），它接收使用者的 ChosenNum 。

函式內部需要驗證輸入的數字是否符合 Bound list 。

如果通過，將 (ChoiceId, ChosenNum) 寫入 contract.choices 。

generate_notify_function (for Notify )：

這也是一個 public fun 。

函式內部呼叫 internal_eval_observation 檢查 Notify 的 observation 。

如果結果為 true，則推進狀態機；否則 assert! 失敗。

generate_let_function (for Let )：

這應該是一個 fun internal_...（像 pay）。

函式內部呼叫 internal_eval_value 計算 value 。

將 (ValueId, result) 寫入 contract.boundValues 。

generate_assert_function (for Assert )：

這也是一個 fun internal_...。

函式內部呼叫 internal_eval_observation 。

如果結果為 false，則 assert!(false, E_ASSERT_FAILED) 。

###

``` rust

module test::Test {
    use sui::coin::{Coin};

    public struct Contract has key{
        id: UID,
        stage: u8,
    }


    fun init(ctx: &mut TxContext){
        let contract =  Contract{
            id: object::new(ctx),
            stage: 0,
        };
        transfer::share_object(contract);
    }

    public entry fun deposit_0<SUI>(
        contract: &mut Contract,
        sender: address,
        receiver: address,
        deposit_coin: &mut Coin<SUI>,
        amount: u64,
        ctx: &mut TxContext
    ){
        assert!(contract.stage ==0 , 1);
        assert!(deposit_coin.value() >= amount, 2 );
        assert!(ctx.sender() == sender, 3);
        transfer::public_transfer(deposit_coin.split(amount, ctx), receiver);
        contract.stage = 1;
    }
}

```
