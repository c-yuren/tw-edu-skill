# 原創題 JSON 契約（V1）

最外層：`{ "title": "...", "questions": [...] }`。

每題必填：`id`, `type`, `stem`, `subject`, `grade`, `unit`, `primary_knowledge_point_id`（系統自訂知識點）, `difficulty` (`D1`–`D4`), `design_intent`, `answer`, `explanation`, `authorship="original"`, `sources`（HTTPS URL 陣列，可為空）, `verification`。

題型：
- `single_choice`: `options` 是 `{ "A":"選項", ... }`；`answer` 是選項鍵。
- `multiple_choice`: 同上；`answer` 是不重複的選項鍵陣列。
- `numeric`: `answer` 是數字、另有 `tolerance`（>=0）與 `unit`（若無單位寫 `無`）。
- `short_answer`/`essay`: `answer` 文字、`rubric` 非空評分規準陣列。

`verification` 結構為五項獨立檢查，每項 `passed: true` + `evidence: "具體驗證"`，以及 `verified_by`, `verified_at`。詳見 `verification-policy.md`。

**不能把 `question-check` 通過解讀為科學或數學正確性的證明**：它只驗證結構與人工/Agent 填寫的驗證聲明，須事先依照驗證流程獨立核對。

正式模考可另外提供 `blueprint.json`：

```json
{"exam":"學測自然（練習）","total_questions":2,"allocations":[{"knowledge_point_id":"HS-PHY-N2-FREEBODY","count":1},{"knowledge_point_id":"HS-PHY-N2-CALC","count":1}]}
```

程式依 `primary_knowledge_point_id` 核對配額。圖表題請以合法原創素材另附檔案，不能用「圖略」造成無法作答。
