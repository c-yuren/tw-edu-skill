#!/usr/bin/env python3
"""Install shared workspace skills for Codex, Antigravity, Claude Code."""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import sys

SKILLS = ("taiwan-education", "taiwan-question-designer", "taiwan-quiz", "taiwan-tutor")


def install(target: Path, agent: str, force: bool = False) -> list[Path]:
    source = Path(__file__).resolve().parent.parent
    target = target.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    roots = []
    if agent in ("all", "codex", "antigravity"):
        roots.append(target / ".agents" / "skills")
    if agent in ("all", "claude"):
        roots.append(target / ".claude" / "skills")
    copies = [(source / "skills" / name, root / name) for root in roots for name in SKILLS]
    copies += [(source / "tools", target / ".taiwan-learning" / "tools"),
               (source / "references", target / ".taiwan-learning" / "references"),
               (source / "examples", target / ".taiwan-learning" / "examples")]
    existing = [str(dest) for _, dest in copies if dest.exists()]
    if existing and not force:
        raise RuntimeError("目標已有檔案；如確定要覆寫本套件檔案，請加 --force:\n" + "\n".join(existing))
    if source == target:
        raise RuntimeError("請安裝到另一個專案目錄；原始碼目錄已包含 Skills")
    installed: list[Path] = []
    for src, dest in copies:
        if dest.exists():
            shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        installed.append(dest)
    gitignore = target / ".gitignore"
    marker = "/.taiwan-learning-data/"
    before = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if marker not in before.splitlines():
        with gitignore.open("a", encoding="utf-8") as f:
            if before and not before.endswith("\n"):
                f.write("\n")
            f.write("\n# Taiwan Learning Skills private records\n" + marker + "\n")
    return installed


def main() -> int:
    ap = argparse.ArgumentParser(description="安裝 Taiwan Learning Skills 到既有 Agent 工作區")
    ap.add_argument("--target", required=True, help="目標專案資料夾（不是 skills 子目錄）")
    ap.add_argument("--agent", default="all", choices=("all", "claude", "codex", "antigravity"))
    ap.add_argument("--force", action="store_true", help="覆寫本套件已存在的技能與參考檔案")
    args = ap.parse_args()
    try:
        paths = install(Path(args.target), args.agent, args.force)
        for path in paths:
            print("installed:", path)
        print("完成。請在目標專案根目錄執行：python .taiwan-learning/tools/learning_cli.py init")
        return 0
    except (OSError, RuntimeError) as e:
        print("安裝失敗：", e, file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
