---
name: taiwan-quiz
description: 進行台灣國高中互動測驗、試卷作答與批改，記錄錯題證據，更新本地 Learning Profile，安排下一輪個人化複習。
---
# Taiwan Quiz — 測驗、批改與學習紀錄

## 啟用時機
學生要開始練習、測驗、交卷、批改、檢查錯題、查看學習紀錄或安排複習。

## 兩種模式
- `practice`: 可逐題作答、選擇 H0–H4 提示；需要時協作 `taiwan-tutor`，答後逐題回饋。
- `mock`: 完整試卷、按設計規則作答；預設交卷後才顯示答案與詳解。不要聲稱單一 Agent 能完全防止作弊。

## 測驗流程
1. 請 `taiwan-question-designer` 建立符合 `taiwan-education` 課綱的原創題和驗證聲明；已有合法題目也可使用。
2. 練習中一次呈現一題；收到學生實際作答再批改。使用者未提供作答，**不可生成虛構作答紀錄**。
3. 批改先用已核實的標準答案、評分規準；數理題要考慮單位與等價答案，開放題允許不同合理表述。對含糊題目先人工審核，不能直接記為錯。
4. 記錄 `hint_level` (0–4)、`question_verified`、`error_type`；不能僅憑答錯就斷言概念錯。個資只使用代號。
5. 按 `.taiwan-learning/references/mastery-policy.md` 的規則把一次作答整理成 JSON，例如 `.taiwan-learning/examples/attempt-example.json`（安裝版示例位置），再執行：
   `python .taiwan-learning/tools/learning_cli.py record --file attempt.json`
6. 查看：`python .taiwan-learning/tools/learning_cli.py profile --student student-001`；複習排序：`python .taiwan-learning/tools/learning_cli.py recommend --student student-001`。
7. 對迷思與錯題轉交 `taiwan-tutor`，完成補強後用新情境題重新驗證。

## 隱私與限制
- 本地 SQLite 預設在目前工作目錄 `.taiwan-learning-data/`，可用 `TW_LEARNING_DATA_DIR` 指向安全的本地共用資料夾。
- 使用者可自行執行 `export` 與 `delete-student`；未經同意不可讀寫其他學生代號資料。
- 只有 `question_verified=true` 且實際完成的作答會影響掌握狀態。CLI 不會自行批改，`is_correct` 必須由已驗證的正確答案判定。
- 同一台機器上 SQLite 可防並行資料庫交易衝突；**不要讓多台機器/跨 VM 直接同時操作共享網路磁碟上的 SQLite DB**。
