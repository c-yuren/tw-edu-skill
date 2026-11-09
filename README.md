# Taiwan Learning Skills V1.0 — 台灣國高中 AI 學習 Skills

> **可執行的第一版**｜純 Skills + Python 標準函式庫 + 本地 SQLite；不需要 MCP、API Key、常駐伺服器或第三方 Python 套件。

提供四個協作 Skill：`taiwan-education`、`taiwan-question-designer`、`taiwan-quiz`、`taiwan-tutor`。適用於支援 `SKILL.md` 的 **Claude Code / Codex / Google Antigravity**；跨 Agent 的實際自動啟用取決於工具版本、權限及是否載入專案 Skills。

## 快速安裝（Windows / macOS / Linux）

需要 Python **3.10 或更新版本**。請將本專案 ZIP 解壓縮後，打開終端機，進入解壓縮的 `taiwan-learning-skills` 目錄：

```bash
# 安裝到另一個已存在或新建立的 Agent 專案；請把路徑改為你自己的
python tools/install.py --target "../my-study-workspace" --agent all

# 在目標專案根目錄下初始化學生紀錄資料庫
cd ../my-study-workspace
python .taiwan-learning/tools/learning_cli.py init
```

Windows 使用 `py -3` 代替 `python` 也可以。**本專案不會自行執行網路請求。**

安裝後資料夾大致如下：

```text
my-study-workspace/
├── .agents/skills/
│   ├── taiwan-education/SKILL.md
│   ├── taiwan-question-designer/SKILL.md
│   ├── taiwan-quiz/SKILL.md
│   └── taiwan-tutor/SKILL.md
├── .claude/skills/            # 同一版本的四個 Skills
├── .taiwan-learning/
│   ├── tools/                 # learning_cli.py
│   ├── references/            # 課綱搜尋、命題、驗證、教學規則
│   └── examples/              # 原創示範題、藍圖與作答紀錄
└── .taiwan-learning-data/     # 本地私有 SQLite 紀錄；預設被 gitignore 忽略
```

### 讓 Agent 使用

在上述 **my-study-workspace** 開啟 Codex、Claude Code 或 Antigravity，試著輸入：

> 請使用 `taiwan-education` 與 `taiwan-tutor`，依台灣高中物理的牛頓第二運動定律，先解釋受力圖，再幫我檢查這題。

或：

> 使用 `taiwan-question-designer`，幫我出 5 題符合高一物理學習階段的原創題，先製作命題藍圖，再獨立驗證答案，讓 `taiwan-quiz` 用互動方式進行。

或：

> 請使用 `taiwan-quiz`，讀取學生代號 `student-001` 的已保存作答證據，推薦下一次複習的知識點。

沒有原生搜尋權限時，Skill 仍可使用本地規則解基本題，但**不能宣稱已核對最新考試規格或已閱讀外部教材**。

## CLI 可用功能

下列命令在**已安裝的專案根目錄**執行；若要在本原始碼目錄直接測試，把路徑 `.taiwan-learning/tools/learning_cli.py` 換成 `tools/learning_cli.py`，範例路徑也換成 `examples/`。

```bash
# 查看官方與可信網站索引，不發任何網路要求
python .taiwan-learning/tools/learning_cli.py sources

# 結構 + 驗證聲明 + 命題藍圖配額檢查
python .taiwan-learning/tools/learning_cli.py question-check \
  --file .taiwan-learning/examples/questions-example.json \
  --blueprint .taiwan-learning/examples/blueprint-example.json

# 學生版（預設不顯示答案）
python .taiwan-learning/tools/learning_cli.py render \
  --file .taiwan-learning/examples/questions-example.json --out student.md --role student

# 教師版（明確要求才產生）
python .taiwan-learning/tools/learning_cli.py render \
  --file .taiwan-learning/examples/questions-example.json --out teacher.md --role teacher

# 記錄一次真實作答前，務必先修改示範檔案的 student_id、attempt_id 與批改結果
python .taiwan-learning/tools/learning_cli.py record \
  --file .taiwan-learning/examples/attempt-example.json

python .taiwan-learning/tools/learning_cli.py profile --student student-001
python .taiwan-learning/tools/learning_cli.py recommend --student student-001

# 匯出（可能包含學生敏感作答資料，請勿分享給無關人士）
python .taiwan-learning/tools/learning_cli.py export --student student-001 --out student-backup.json

# 刪除本地學生作答紀錄（無法復原，請先備份）
python .taiwan-learning/tools/learning_cli.py delete-student \
  --student student-001 --confirm student-001
```

上述命令中的 `\` 是 macOS/Linux 的換行符號；**Windows PowerShell 可將整條指令寫在同一行**。

## 個人化能力評估設計

- 已確認：**多維證據評估、平衡型難度策略**。依知識點整理已驗證題目作答、不同題型、提示、不同情境與日期。
- `未評估` / `學習中` / `初步掌握` / `穩定掌握` / `需要複習`；Tutor 的 `L1–L4` 是**教學深度建議**，不等於題目難度 `D1–D4`。
- `profile` 報告包含明確可追溯的證據與判定可信度；`recommend` 根據弱點與近期錯題排序。
- 這是可解釋的初版規則，**不是經過教育測量研究驗證的學力診斷模型**。評估可能會誤差，不能只憑系統分級做重要決策。

## 命題嚴格驗證的範圍

命題前先規劃知識點與能力，正式模考需先展示藍圖。每道題在 JSON 中保存：題幹、選項/答案、詳解、命題意圖、授權/來源、五項驗證聲明。Python 可檢查欄位、題號、選項、驗證聲明、命題藍圖配額。

**Important:** Python 不會自己推導所有數學答案，也無法保證 Agent 沒有虛構驗證證據。出題 Agent 仍必須完成**獨立解答、內容驗證**；正式模考建議教師抽查。若無法核對，應標記未驗證，不可將其冒充已驗證試題。

## 網路、授權與實際限制

- 內建來源：國家教育研究院課綱、教育大市集、大考中心、國中教育會考、均一、因材網等索引。
- **沒有爬蟲**。原生網路搜尋由使用者的 Agent 執行，若平台無法讀到某頁，需如實回報。
- 不附帶受保護的出版社講義、官方歷屆試題全文；原創題是本專案自行編寫的示範題。
- `.taiwan-learning-data/` 在專案根目錄保存原始作答證據，預設不會上傳。學生可匯出與刪除。
- SQLite 適合**同一台電腦本機**的多 Agent 存取。**不同電腦、跨虛擬機且透過 NFS/SMB 等共享磁碟同時寫同一個 DB 不支援**；建議單一主機負責寫入，或改為安全的匯出匯入方案後再擴充。
- `--data-dir` 或 `TW_LEARNING_DATA_DIR` 可以指定本機其他持久化位置；不同工作區需要明確使用相同本地路徑才會共用紀錄。
- 安裝器預設拒絕覆寫既有同名 Skills，若要更新套件可使用 `--force`（會覆寫**本套件技能與參考檔**，不會覆寫學生資料）。
- 正式學測/會考題型與內容可能更新，必須使用原生搜尋確認當年度官方資訊。

## 原始碼目錄

- `skills/`：四個可直接讀取的 Agent Skills。
- `references/`：可信來源、課綱、命題特徵、驗證與 Tutor/掌握規則。
- `tools/learning_cli.py`：初始化、記錄作答、分析、複習、驗證題庫、渲染試卷。
- `tools/install.py`：在工作區自動建立 Claude/Codex/Antigravity 技能目錄。
- `examples/`：3 道原創物理示範題與命題藍圖／作答紀錄。
- `tests/`：標準函式庫 unittest 測試。

## 測試

```bash
python -m unittest discover -s tests -v
```

**V1.0 範圍：** 可執行的 Skills + 工具 + 範例 + 測試；沒有真正自動的整科網頁教材爬取/下載、學測歷屆題庫、獨立 LLM API、完備 PDF/DOCX 輸出或教育研究式診斷效度。這些需要後續按授權、工具可用性及使用需求擴充。
