import json
from parser import parse_contract
from fsm_model import parse_contract_to_infos
from move_generator import generate_module, build_stage_lookup # (FIXED) 匯入 build_stage_lookup

def main():
    """
    主執行腳本：
    1. 載入 Marlowe JSON
    2. 解析為 AST
    3. 將 AST 轉換為 StageInfo 藍圖
    4. 建立 Stage 查找表
    5. 產生 Move 程式碼
    6. 寫入檔案
    """
    input_filename = "swap_ada.json"
    output_filename = "generated_contract.move"

    try:
        # 1. 載入 json 合約檔
        with open(input_filename, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        print(f"1. 成功從 '{input_filename}' 載入 Marlowe JSON。")

        # 2. 解析為 AST
        contract_ast = parse_contract(json_data)
        print("2. 成功將 JSON 解析為 Marlowe AST。")

        # 3. (FIXED) 將 AST 轉換為 StageInfo 藍圖
        #    我們需要傳入 stage=0 並接收 (infos, max_stage)
        (infos, max_stage) = parse_contract_to_infos(contract_ast, stage=0)
        print(f"3. 成功分析 AST。總共偵測到 {max_stage} 個唯一的 stages。")

        # 4. (FIXED) 建立 Stage 查找表 (自動化鏈的關鍵)
        stage_lookup = build_stage_lookup(infos)
        print("4. 成功建立 Stage 查找表。")

        # 5. (FIXED) 產生 Move 程式碼
        #    我們需要傳入 infos 和 stage_lookup
        move_code = generate_module(infos, stage_lookup)
        print("5. 成功產生 Move 程式碼。")

        # 6. 寫出 .move 檔
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(move_code)

        print(f"\n✅ 成功！ Move 程式碼已儲存至 '{output_filename}'")

    except FileNotFoundError:
        print(f"錯誤: 找不到輸入檔案 '{input_filename}'。")
    except (ValueError, KeyError, AttributeError) as e:
        print(f"\n❌ 處理合約時發生錯誤: {e}")
        print("請檢查 'parser.py' 和 'fsm_model.py' 是否已更新至最新版本。")
        raise # 顯示完整的錯誤堆疊

if __name__ == "__main__":
    main()
