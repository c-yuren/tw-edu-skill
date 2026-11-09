#!/usr/bin/env python3
"""Taiwan Learning Skills — dependency-free, local first CLI (Python >=3.10).

This tool never downloads third-party copyrighted materials or sends student data online.
The agent's native search is responsible for accessing fresh official references.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

STUDENT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
QUESTION_TYPES = {"single_choice", "multiple_choice", "numeric", "short_answer", "essay"}
ERROR_TYPES = {"concept", "method", "reading", "calculation", "units", "reasoning", "unknown", "none"}
VERIFICATION_CHECKS = ("curriculum", "independent_solution", "ambiguity", "explanation", "rights")


def cli_root() -> Path:
    return Path(__file__).resolve().parent.parent


def data_root(args: argparse.Namespace) -> Path:
    explicit = getattr(args, "data_dir", None) or os.getenv("TW_LEARNING_DATA_DIR")
    return Path(explicit).expanduser().resolve() if explicit else (Path.cwd() / ".taiwan-learning-data").resolve()


def database_path(args: argparse.Namespace) -> Path:
    return data_root(args) / "learning.sqlite3"


def connect(args: argparse.Namespace) -> sqlite3.Connection:
    root = data_root(args)
    root.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        try:
            root.chmod(0o700)
        except OSError:
            pass
    db = sqlite3.connect(database_path(args), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA foreign_keys=ON")
    # WAL works well on one local host; DO NOT share a live SQLite DB across NFS/VM shared folders.
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
       CREATE TABLE IF NOT EXISTS students (
           student_id TEXT PRIMARY KEY,
           created_at TEXT NOT NULL
       );
       CREATE TABLE IF NOT EXISTS attempts (
           attempt_id TEXT PRIMARY KEY,
           student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
           timestamp TEXT NOT NULL,
           question_id TEXT NOT NULL,
           subject TEXT NOT NULL,
           grade TEXT NOT NULL,
           unit TEXT NOT NULL,
           knowledge_point_id TEXT NOT NULL,
           question_type TEXT NOT NULL,
           context_id TEXT NOT NULL,
           difficulty INTEGER NOT NULL,
           is_correct INTEGER NOT NULL,
           hint_level INTEGER NOT NULL,
           question_verified INTEGER NOT NULL,
           error_type TEXT NOT NULL,
           mode TEXT NOT NULL,
           detail TEXT NOT NULL DEFAULT ''
       );
       CREATE INDEX IF NOT EXISTS attempts_learner_idx
            ON attempts(student_id, subject, knowledge_point_id, timestamp);
    """)
    return db


def dump(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def read_json(filename: str) -> Any:
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def required_string(value: Any, label: str, errors: list[str], minimum: int = 1) -> bool:
    ok = isinstance(value, str) and len(value.strip()) >= minimum
    if not ok:
        errors.append(f"{label}: 必須是非空字串")
    return ok


def is_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        url = urlparse(value)
        return url.scheme == "https" and bool(url.hostname)
    except ValueError:
        return False


def validate_question_bundle(bundle: Any, strict: bool = True, blueprint: Any = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(bundle, dict) or not isinstance(bundle.get("questions"), list):
        return ["根節點必須是物件，包含 questions 陣列"]
    questions = bundle["questions"]
    if not questions:
        errors.append("questions 不可為空")
    ids: set[str] = set()
    stems: set[str] = set()
    counts: dict[str, int] = defaultdict(int)
    for i, q in enumerate(questions, 1):
        prefix = f"questions[{i}]"
        if not isinstance(q, dict):
            errors.append(f"{prefix}: 必須是物件")
            continue
        for key in ("id", "stem", "subject", "grade", "unit", "primary_knowledge_point_id", "explanation", "design_intent"):
            required_string(q.get(key), f"{prefix}.{key}", errors)
        qid = q.get("id")
        if isinstance(qid, str):
            if qid in ids:
                errors.append(f"{prefix}: 重複題目 id {qid}")
            ids.add(qid)
        stem = q.get("stem")
        if isinstance(stem, str):
            normalized = re.sub(r"\s+", "", stem)
            if normalized in stems:
                errors.append(f"{prefix}: 題幹重複")
            stems.add(normalized)
        kp = q.get("primary_knowledge_point_id")
        if isinstance(kp, str):
            counts[kp] += 1
        typ = q.get("type")
        if typ not in QUESTION_TYPES:
            errors.append(f"{prefix}.type: 不支援的題型 {typ}")
        if q.get("difficulty") not in ("D1", "D2", "D3", "D4"):
            errors.append(f"{prefix}.difficulty: 必須是 D1~D4")
        if q.get("authorship") != "original":
            errors.append(f"{prefix}.authorship: 此版本只接受 original，真題請提供連結")
        answer = q.get("answer")
        if typ in {"single_choice", "multiple_choice"}:
            options = q.get("options")
            if not isinstance(options, dict) or len(options) < 2:
                errors.append(f"{prefix}.options: 至少兩個選項的物件")
            else:
                if any(not isinstance(k, str) or not isinstance(v, str) or not v.strip() for k, v in options.items()):
                    errors.append(f"{prefix}.options: 選項鍵和值必須是非空字串")
                normalized_options = [re.sub(r"\s+", "", val) for val in options.values()]
                if len(set(normalized_options)) != len(normalized_options):
                    errors.append(f"{prefix}.options: 出現重複選項")
                if typ == "single_choice" and (not isinstance(answer, str) or answer not in options):
                    errors.append(f"{prefix}.answer: 單選答案必須是有效選項鍵")
                if typ == "multiple_choice" and (
                    not isinstance(answer, list) or not answer or
                    any(not isinstance(k, str) or k not in options for k in answer) or
                    len(set(map(str, answer))) != len(answer)
                ):
                    errors.append(f"{prefix}.answer: 多選答案必須是無重複且有效的選項鍵陣列")
        elif typ == "numeric":
            if isinstance(answer, bool) or not isinstance(answer, (int, float)):
                errors.append(f"{prefix}.answer: 數值題必須提供數字")
            if isinstance(q.get("tolerance"), bool) or not isinstance(q.get("tolerance"), (int, float)) or q["tolerance"] < 0:
                errors.append(f"{prefix}.tolerance: 必須為 >=0 的數值")
            required_string(q.get("unit"), f"{prefix}.unit", errors)
        elif typ in {"short_answer", "essay"}:
            required_string(answer, f"{prefix}.answer", errors)
            rubric = q.get("rubric")
            if not isinstance(rubric, list) or not rubric or not all(isinstance(x, str) and x.strip() for x in rubric):
                errors.append(f"{prefix}.rubric: 開放題必須提供評分規準清單")
        sources = q.get("sources", [])
        if not isinstance(sources, list) or not all(is_http_url(x) for x in sources):
            errors.append(f"{prefix}.sources: 必須是 HTTPS URL 陣列")
        if strict:
            verification = q.get("verification")
            if not isinstance(verification, dict):
                errors.append(f"{prefix}.verification: 嚴格模式必須提供驗證聲明")
            else:
                for name in VERIFICATION_CHECKS:
                    check = verification.get(name)
                    if not isinstance(check, dict) or check.get("passed") is not True or not isinstance(check.get("evidence"), str) or len(check["evidence"].strip()) < 4:
                        errors.append(f"{prefix}.verification.{name}: 須 passed=true 且包含具體 evidence")
                required_string(verification.get("verified_by"), f"{prefix}.verification.verified_by", errors)
                required_string(verification.get("verified_at"), f"{prefix}.verification.verified_at", errors)
    if blueprint is not None:
        if not isinstance(blueprint, dict) or not isinstance(blueprint.get("allocations"), list):
            errors.append("blueprint: 需要 allocations 陣列")
        else:
            allocations = blueprint["allocations"]
            desired: dict[str, int] = {}
            for a in allocations:
                if (not isinstance(a, dict) or not isinstance(a.get("knowledge_point_id"), str) or
                        isinstance(a.get("count"), bool) or not isinstance(a.get("count"), int) or a["count"] < 0):
                    errors.append("blueprint.allocations: 知識點 ID 或 count 不正確")
                    continue
                k = a["knowledge_point_id"]
                if k in desired:
                    errors.append(f"blueprint.allocations: 重複知識點 {k}")
                desired[k] = a["count"]
            if sum(desired.values()) != len(questions):
                errors.append("blueprint: 規劃總題數與實際題數不一致")
            if dict(counts) != {k: v for k, v in desired.items() if v > 0}:
                errors.append(f"blueprint: 實際知識點配額 {dict(counts)} 不符合規劃 {desired}")
    return errors


def safe_markdown(s: str) -> str:
    # Keep math and formatting; prevent accidental fenced blocks from disrupting output.
    return s.replace("```", "` ` `")


def render_questions(bundle: dict[str, Any], teacher: bool) -> str:
    name = bundle.get("title", "台灣國高中練習題")
    out = [f"# {safe_markdown(str(name))}", "", "原創試題；非官方考題。", ""]
    for i, q in enumerate(bundle["questions"], 1):
        out.extend([f"## 第 {i} 題（{q['difficulty']}）", "", safe_markdown(q["stem"]), ""])
        if q["type"] in ("single_choice", "multiple_choice"):
            out.extend(f"- {letter}. {safe_markdown(value)}" for letter, value in q["options"].items())
            out.append("")
        else:
            out.extend(["作答：________________________________", ""])
        if teacher:
            answer = q["answer"]
            out.extend([f"**標準答案：** {', '.join(answer) if isinstance(answer, list) else answer}", "",
                        f"**詳解：** {safe_markdown(q['explanation'])}", "",
                        f"**命題意圖：** {safe_markdown(q['design_intent'])}", "",
                        f"**知識點：** `{q['primary_knowledge_point_id']}`", ""])
            if q.get("rubric"):
                out.extend(["**評分規準：**", *[f"- {r}" for r in q["rubric"]], ""])
            if q.get("sources"):
                out.extend(["**參考來源：**", *[f"- {u}" for u in q["sources"]], ""])
    return "\n".join(out).rstrip() + "\n"


def validate_attempt(a: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(a, dict):
        return ["作答紀錄需為 JSON 物件"]
    for field in ("student_id", "question_id", "subject", "grade", "unit", "knowledge_point_id", "question_type", "context_id"):
        required_string(a.get(field), field, errors)
    if isinstance(a.get("student_id"), str) and not STUDENT_ID_PATTERN.fullmatch(a["student_id"]):
        errors.append("student_id: 請使用非識別性代號（英數、點、底線、連字號，最多64字）")
    if a.get("question_type") not in QUESTION_TYPES:
        errors.append("question_type: 不支援")
    if a.get("difficulty") not in (1, 2, 3, 4):
        errors.append("difficulty: 需為 1~4")
    if not isinstance(a.get("is_correct"), bool):
        errors.append("is_correct: 必須為 true/false")
    if a.get("hint_level") not in range(5):
        errors.append("hint_level: 需為 0~4")
    if not isinstance(a.get("question_verified"), bool):
        errors.append("question_verified: 必須為 true/false")
    if a.get("error_type") not in ERROR_TYPES:
        errors.append(f"error_type: 限 {', '.join(sorted(ERROR_TYPES))}")
    if a.get("mode") not in ("practice", "mock", "diagnostic"):
        errors.append("mode: 限 practice/mock/diagnostic")
    if a.get("is_correct") is True and a.get("error_type") not in ("none", "unknown"):
        errors.append("正確作答的 error_type 應為 none 或 unknown")
    if a.get("is_correct") is False and a.get("error_type") == "none":
        errors.append("錯誤作答的 error_type 不可為 none")
    if "attempt_id" in a and (not isinstance(a["attempt_id"], str) or not STUDENT_ID_PATTERN.fullmatch(a["attempt_id"])):
        errors.append("attempt_id 格式不正確")
    return errors


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def insert_attempt(args: argparse.Namespace, a: dict[str, Any]) -> dict[str, Any]:
    errors = validate_attempt(a)
    if errors:
        return {"ok": False, "errors": errors}
    aid = a.get("attempt_id") or uuid4().hex
    timestamp = a.get("timestamp") or utc_now()
    try:
        dt = datetime.fromisoformat(timestamp)
        if dt.tzinfo is None:
            raise ValueError("timezone missing")
    except (ValueError, TypeError):
        return {"ok": False, "errors": ["timestamp 需要有時區的 ISO8601 字串"]}
    db = connect(args)
    try:
        with db:
            db.execute("INSERT OR IGNORE INTO students(student_id,created_at) VALUES (?,?)", (a["student_id"], utc_now()))
            cur = db.execute("""INSERT OR IGNORE INTO attempts (
                attempt_id,student_id,timestamp,question_id,subject,grade,unit,knowledge_point_id,
                question_type,context_id,difficulty,is_correct,hint_level,question_verified,error_type,mode,detail
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                aid, a["student_id"], timestamp, a["question_id"], a["subject"], a["grade"], a["unit"],
                a["knowledge_point_id"], a["question_type"], a["context_id"], a["difficulty"],
                int(a["is_correct"]), a["hint_level"], int(a["question_verified"]), a["error_type"],
                a["mode"], a.get("detail", "")[:2000]
            ))
        return {"ok": True, "attempt_id": aid, "inserted": cur.rowcount == 1,
                "counted_in_mastery": a["question_verified"]}
    finally:
        db.close()


def summarize_one(rows: list[sqlite3.Row]) -> dict[str, Any]:
    valid = [r for r in rows if r["question_verified"]]
    n = len(valid)
    total = len(rows)
    if n == 0:
        return {"mastery": "未評估", "teaching_level": None, "confidence": "證據不足", "attempts": total,
                "verified_attempts": 0, "independent_correct": 0, "evidence": "沒有已驗證題目的作答證據"}
    independent_correct = [r for r in valid if r["is_correct"] and r["hint_level"] == 0]
    qtypes = {r["question_type"] for r in independent_correct}
    contexts = {r["context_id"] for r in independent_correct}
    days = {r["timestamp"][:10] for r in independent_correct}
    uniq_ids = {r["question_id"] for r in independent_correct}
    recent = valid[-3:]
    wrong_recent = sum(not r["is_correct"] for r in recent)
    if (len(uniq_ids) >= 4 and len(qtypes) >= 2 and len(contexts) >= 2 and len(days) >= 2
            and wrong_recent < 2):
        mastery = "穩定掌握"
    elif len(uniq_ids) >= 2:
        mastery = "初步掌握"
    else:
        mastery = "學習中"
    if len(uniq_ids) >= 3 and len(valid) >= 4 and wrong_recent >= 2:
        mastery = "需要複習"
    if n >= 6 and len(qtypes) >= 2 and len(days) >= 2 and len(contexts) >= 2:
        confidence = "高"
    elif n >= 3 and len(qtypes) >= 2:
        confidence = "中"
    else:
        confidence = "低"
    if n < 2:
        level = None
    elif mastery == "穩定掌握":
        hard_ids = {r["question_id"] for r in independent_correct if r["difficulty"] >= 3}
        level = "L4" if len(hard_ids) >= 2 and len(contexts) >= 2 else "L3"
    else:
        level = "L2" if independent_correct else "L1"
    return {"mastery": mastery, "teaching_level": level, "confidence": confidence,
            "attempts": total, "verified_attempts": n, "independent_correct": len(uniq_ids),
            "verified_correct_rate": round(sum(r["is_correct"] for r in valid) / n, 3),
            "question_types": sorted(qtypes), "contexts": len(contexts), "days": len(days),
            "recent_incorrect": wrong_recent,
            "evidence": f"{n} 筆有效證據；{len(uniq_ids)} 道不同題目獨立答對；{len(qtypes)} 題型；{len(contexts)} 情境；{len(days)} 日期"}


def student_report(args: argparse.Namespace) -> dict[str, Any]:
    student = args.student
    if not STUDENT_ID_PATTERN.fullmatch(student):
        return {"ok": False, "error": "student ID 格式不正確"}
    db = connect(args)
    try:
        rows = db.execute("""SELECT * FROM attempts WHERE student_id=? ORDER BY timestamp, rowid""", (student,)).fetchall()
    finally:
        db.close()
    grouped: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        grouped[(r["subject"], r["knowledge_point_id"])].append(r)
    result = []
    for (subject, point), records in grouped.items():
        info = summarize_one(records)
        last = records[-1]
        result.append({"subject": subject, "knowledge_point_id": point, "grade": last["grade"],
                       "unit": last["unit"], "last_seen": last["timestamp"], **info})
    return {"ok": True, "student_id": student, "total_attempts": len(rows),
            "knowledge_points": sorted(result, key=lambda x: (x["subject"], x["knowledge_point_id"]))}


def recommend(report: dict[str, Any]) -> dict[str, Any]:
    choices = []
    for point in report.get("knowledge_points", []):
        mastery = point["mastery"]
        score = (5 if mastery == "需要複習" else 4 if mastery == "學習中" else 3 if mastery == "初步掌握" else 2)
        score += min(2, point.get("recent_incorrect", 0))
        score += 1 if point.get("confidence") in ("低", "證據不足") else 0
        if mastery == "穩定掌握":
            action = "跨情境挑戰或維持性複習"
        elif mastery == "需要複習":
            action = "Tutor 先釐清近期錯誤，再設計不同情境的驗證題"
        elif mastery == "初步掌握":
            action = "維持 D2-D3，換題型測試自主應用"
        else:
            action = "由 Tutor 檢查先備觀念，再安排 D1-D2 診斷或補強題"
        choices.append({"subject": point["subject"], "knowledge_point_id": point["knowledge_point_id"],
                        "priority": score, "action": action, "reason": point["evidence"]})
    choices.sort(key=lambda x: (-x["priority"], x["subject"], x["knowledge_point_id"]))
    return {"student_id": report.get("student_id"), "recommendations": choices}


def student_export(args: argparse.Namespace) -> dict[str, Any]:
    db = connect(args)
    try:
        rows = db.execute("SELECT * FROM attempts WHERE student_id=? ORDER BY timestamp, rowid", (args.student,)).fetchall()
        exists = db.execute("SELECT 1 FROM students WHERE student_id=?", (args.student,)).fetchone() is not None
    finally:
        db.close()
    if not exists:
        return {"ok": False, "error": "找不到學生代號"}
    content = {"schema_version": 1, "student_id": args.student, "attempts": [dict(r) for r in rows]}
    target = Path(args.out).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "file": str(target), "attempts": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description="台灣國高中 Learning Skills：本地作答紀錄、命題檢查與試卷輸出")
    parser.add_argument("--data-dir", help="資料目錄；預設目前工作目錄/.taiwan-learning-data，亦可用 TW_LEARNING_DATA_DIR")
    commands = parser.add_subparsers(dest="cmd", required=True)
    commands.add_parser("init", help="初始化本地資料庫")
    record = commands.add_parser("record", help="記錄一次作答（從 JSON 讀取）")
    record.add_argument("--file", required=True)
    report = commands.add_parser("profile", help="顯示學生掌握狀態")
    report.add_argument("--student", required=True)
    rec = commands.add_parser("recommend", help="自動排序下一步複習")
    rec.add_argument("--student", required=True)
    verify = commands.add_parser("question-check", help="檢查題目結構與驗證聲明")
    verify.add_argument("--file", required=True)
    verify.add_argument("--blueprint")
    verify.add_argument("--draft", action="store_true", help="只做基礎檢查；不能以此宣稱嚴格驗證通過")
    render = commands.add_parser("render", help="產生學生版或教師版 Markdown")
    render.add_argument("--file", required=True)
    render.add_argument("--out", required=True)
    render.add_argument("--role", choices=("student", "teacher"), default="student")
    render.add_argument("--blueprint")
    commands.add_parser("sources", help="顯示可信來源清單（網址索引，不抓取）")
    export = commands.add_parser("export", help="匯出學生資料以供查閱/備份")
    export.add_argument("--student", required=True)
    export.add_argument("--out", required=True)
    deletion = commands.add_parser("delete-student", help="刪除一位學生的本地紀錄")
    deletion.add_argument("--student", required=True)
    deletion.add_argument("--confirm", required=True, help="必須與 student 代號一致")
    args = parser.parse_args()
    try:
        if args.cmd == "init":
            db = connect(args)
            db.close()
            dump({"ok": True, "database": str(database_path(args)), "network_used": False})
        elif args.cmd == "record":
            result = insert_attempt(args, read_json(args.file))
            dump(result)
            return 0 if result["ok"] else 2
        elif args.cmd in ("profile", "recommend"):
            result = student_report(args)
            if args.cmd == "recommend" and result.get("ok"):
                result = recommend(result)
            dump(result)
            return 0 if result.get("ok") else 2
        elif args.cmd == "question-check":
            blueprint = read_json(args.blueprint) if args.blueprint else None
            errors = validate_question_bundle(read_json(args.file), strict=not args.draft, blueprint=blueprint)
            dump({"ok": not errors, "strict": not args.draft, "errors": errors,
                  "notice": "僅檢查結構與驗證聲明是否齊備，不能取代獨立解題或教師審核"})
            return 0 if not errors else 2
        elif args.cmd == "render":
            bundle = read_json(args.file)
            errors = validate_question_bundle(bundle, strict=True, blueprint=read_json(args.blueprint) if args.blueprint else None)
            if errors:
                dump({"ok": False, "errors": errors})
                return 2
            target = Path(args.out).expanduser().resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_questions(bundle, teacher=args.role == "teacher"), encoding="utf-8")
            dump({"ok": True, "file": str(target), "role": args.role})
        elif args.cmd == "sources":
            path = cli_root() / "references" / "sources.json"
            dump(read_json(str(path)))
        elif args.cmd == "export":
            result = student_export(args)
            dump(result)
            return 0 if result["ok"] else 2
        elif args.cmd == "delete-student":
            if args.student != args.confirm or not STUDENT_ID_PATTERN.fullmatch(args.student):
                dump({"ok": False, "error": "需輸入同一學生代號作為確認"})
                return 2
            db = connect(args)
            try:
                with db:
                    cursor = db.execute("DELETE FROM students WHERE student_id=?", (args.student,))
                dump({"ok": True, "deleted": cursor.rowcount > 0})
            finally:
                db.close()
        return 0
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as ex:
        dump({"ok": False, "error": str(ex)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
