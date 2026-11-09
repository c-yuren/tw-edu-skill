---
name: taiwan-question-designer
description: 台灣國高中原創練習題、會考學測分科模擬命題；先建命題藍圖，分析官方命題特徵，執行答案與題目嚴格驗證，再輸出題庫或試卷。
---
# Taiwan Question Designer — 原創命題與品質驗證

## 啟用時機
需要命題、出題、題型設計、模擬考、單元練習或依學生程度調整題目時。

## 已確定的系統規則
- 兩種模式：個人化練習＋正式試卷。智慧題型配置；根據能力、科目與已核實的官方考試規格決定題型。
- 命題特徵：內建具體考法與考查能力分析；特定年度/高擬真模考必須以原生搜尋重新核對。不能只寫「模仿學測出題習慣」。
- 命題藍圖 C：一般練習內部自動設計；正式試卷／大型模考 **先展示藍圖供使用者審核** 再命題。
- 難度平衡型自適應：題目 `D1`～`D4` 是認知負荷/推理複雜度，不等於學生 Tutor `L1`～`L4` 教學階段。單題失敗不立即降低能力判定。
- 題目原創為主，過往真題**提供官方連結**供延伸，不直接複製或僅替換數字改寫受保護題目。
- 驗證 A：所有題目嚴格檢查；未通過不得納入正式試卷。
- 輸出 A：普通練習優先互動題、正式考試優先試卷、需要資料交換時用 JSON；學生卷和答案卷分開。

## 每次命題步驟
1. 識別年級、科目、課綱單元、模式、題量、目標能力；需要時遵循 `taiwan-education` 的查證流程。
2. 讀 `.taiwan-learning/references/exam-patterns/`（gsat/cap/ast）與 `curriculum-guide.md`；特定正式考試先核對最新官方說明、考查能力、題型、難度來源。區分官方規格、觀察與自己的規劃。
3. 規劃每題 `primary_knowledge_point_id`, 能力目標, type, difficulty, 設計意圖、干擾選項理由。正式試卷先展示題型配額、單元、能力及難度分布供審核。
4. 原創命題，生成答案及推導、選項干擾理由；盡量包含不同情境，不只是換數字。
5. 依 `.taiwan-learning/references/verification-policy.md` 驗證；獨立重解、選項唯一性、詳解、課綱、授權、歧義。若有程式執行工具，數理題加上獨立計算。
6. 生成 JSON 格式遵循 `.taiwan-learning/references/question-schema.md`。執行：
   - `python .taiwan-learning/tools/learning_cli.py question-check --file questions.json`
   - 有命題藍圖時加 `--blueprint blueprint.json`
   - 工具只檢查結構與驗證聲明；**不能將通過當成答案經獨立科學驗證**。
7. 若需試卷：`python .taiwan-learning/tools/learning_cli.py render --file questions.json --out student.md --role student`；教師詳解只在明確需要時以 `--role teacher` 輸出至不同檔案。

## 未完成條件
- 搜尋不可用時不得冒充符合「最新學測某年」；改為一般練習或先向使用者說明。
- 任何來源授權不明時不要重製既有試題。
- 檢查失敗要修題、重新驗證，不能修改 JSON 旗標假裝通過。
