# CLI & TUI 使用說明

本專案提供兩種介面來編譯 Marlowe 合約：命令列介面 (CLI) 和終端圖形介面 (TUI)。

## 環境設定

```bash
# 使用 uv 建立虛擬環境並安裝依賴
uv sync
```

---

## CLI 命令列介面

從專案根目錄執行：

```bash
# 列出所有可用的 spec 檔案
uv run python generator/cli.py list

# 驗證 spec 格式
uv run python generator/cli.py validate              # 驗證全部
uv run python generator/cli.py validate --spec swap_ada  # 驗證單一檔案

# 編譯生成 Move + TypeScript 代碼
uv run python generator/cli.py build                 # 編譯全部
uv run python generator/cli.py build --spec swap_ada # 編譯單一檔案

# 部署到 Sui 網絡
uv run python generator/cli.py deploy
```

---

## TUI 終端圖形介面

```bash
# 從 generator 目錄啟動
cd generator
uv run python tui.py
```

### 快捷鍵

| 按鍵 | 功能 |
|------|------|
| `↑` `↓` | 選擇 spec |
| `b` | Build 編譯 |
| `v` | Validate 驗證 |
| `d` | Deploy 部署 |
| `r` | Refresh 刷新列表 |
| `?` | Help 幫助 |
| `q` | Quit 退出 |

---

## 輸出位置

| 輸出類型 | 路徑 |
|----------|------|
| Move 合約 | `contract/sources/{name}.move` |
| Move 測試 | `contract/tests/{name}_tests.move` |
| TypeScript SDK | `sdk/{name}_sdk.ts` |
| 部署資訊 | `deployments/deployment.json` |
