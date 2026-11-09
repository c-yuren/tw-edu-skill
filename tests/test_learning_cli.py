from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("learning_cli", ROOT / "tools" / "learning_cli.py")
assert spec and spec.loader
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

installer_spec = importlib.util.spec_from_file_location("install_tool", ROOT / "tools" / "install.py")
assert installer_spec and installer_spec.loader
installer = importlib.util.module_from_spec(installer_spec)
installer_spec.loader.exec_module(installer)


def sample_attempt(aid="a1", qid="q1", correct=True, hint=0, verified=True, kind="single_choice", context="first"):
    return {"attempt_id": aid, "student_id": "student-001", "question_id": qid,
            "subject": "物理", "grade": "高中", "unit": "牛頓運動定律",
            "knowledge_point_id": "HS-PHY-N2", "question_type": kind,
            "context_id": context, "difficulty": 2, "is_correct": correct,
            "hint_level": hint, "question_verified": verified,
            "error_type": "none" if correct else "concept", "mode": "practice"}


class LearningCliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.args = SimpleNamespace(data_dir=self.temp.name, student="student-001")

    def tearDown(self):
        self.temp.cleanup()

    def test_example_questions_strict_and_blueprint(self):
        questions = cli.read_json(str(ROOT / "examples" / "questions-example.json"))
        blueprint = cli.read_json(str(ROOT / "examples" / "blueprint-example.json"))
        self.assertEqual(cli.validate_question_bundle(questions, blueprint=blueprint), [])
        blueprint["allocations"][0]["count"] = 7
        self.assertTrue(cli.validate_question_bundle(questions, blueprint=blueprint))

    def test_cannot_pass_question_with_wrong_choice(self):
        questions = cli.read_json(str(ROOT / "examples" / "questions-example.json"))
        questions["questions"][0]["answer"] = "Z"
        self.assertTrue(any("單選答案" in e for e in cli.validate_question_bundle(questions)))

    def test_strict_requires_verification(self):
        questions = cli.read_json(str(ROOT / "examples" / "questions-example.json"))
        questions["questions"][0].pop("verification")
        self.assertTrue(cli.validate_question_bundle(questions))
        self.assertEqual(cli.validate_question_bundle(questions, strict=False), [])

    def test_student_render_hides_answers(self):
        questions = cli.read_json(str(ROOT / "examples" / "questions-example.json"))
        student = cli.render_questions(questions, teacher=False)
        teacher = cli.render_questions(questions, teacher=True)
        self.assertNotIn("**標準答案：**", student)
        self.assertNotIn("**詳解：**", student)
        self.assertIn("**標準答案：**", teacher)
        self.assertIn("a=F合/m", teacher)

    def test_record_and_profile(self):
        r1 = cli.insert_attempt(self.args, sample_attempt())
        self.assertTrue(r1["ok"])
        self.assertTrue(r1["inserted"])
        duplicate = cli.insert_attempt(self.args, sample_attempt())
        self.assertFalse(duplicate["inserted"])
        p = cli.student_report(self.args)
        self.assertEqual(p["total_attempts"], 1)
        self.assertEqual(p["knowledge_points"][0]["mastery"], "學習中")
        self.assertEqual(p["knowledge_points"][0]["teaching_level"], None)
        self.assertEqual(p["knowledge_points"][0]["confidence"], "低")

    def test_unverified_does_not_update_mastery(self):
        cli.insert_attempt(self.args, sample_attempt(verified=False))
        p = cli.student_report(self.args)
        self.assertEqual(p["knowledge_points"][0]["mastery"], "未評估")
        self.assertEqual(p["knowledge_points"][0]["verified_attempts"], 0)

    def test_initial_mastery_two_distinct_independent(self):
        cli.insert_attempt(self.args, sample_attempt())
        cli.insert_attempt(self.args, sample_attempt("a2", "q2", kind="numeric", context="second"))
        p = cli.student_report(self.args)["knowledge_points"][0]
        self.assertEqual(p["mastery"], "初步掌握")
        self.assertEqual(p["independent_correct"], 2)
        self.assertEqual(p["confidence"], "低")

    def test_hinted_does_not_raise_independent_mastery(self):
        cli.insert_attempt(self.args, sample_attempt())
        cli.insert_attempt(self.args, sample_attempt("a2", "q2", hint=2))
        p = cli.student_report(self.args)["knowledge_points"][0]
        self.assertEqual(p["independent_correct"], 1)
        self.assertEqual(p["mastery"], "學習中")

    def test_validation_rejects_missing_evidence(self):
        bad = sample_attempt()
        bad["error_type"] = "concept"
        self.assertTrue(cli.validate_attempt(bad))

    def test_recommend(self):
        cli.insert_attempt(self.args, sample_attempt(correct=False))
        p = cli.student_report(self.args)
        recs = cli.recommend(p)["recommendations"]
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["knowledge_point_id"], "HS-PHY-N2")

    def test_export_and_delete(self):
        cli.insert_attempt(self.args, sample_attempt())
        self.args.out = str(Path(self.temp.name) / "export.json")
        result = cli.student_export(self.args)
        self.assertTrue(result["ok"])
        content = json.loads(Path(self.args.out).read_text(encoding="utf-8"))
        self.assertEqual(len(content["attempts"]), 1)
        db = cli.connect(self.args)
        with db:
            db.execute("DELETE FROM students WHERE student_id=?", (self.args.student,))
        self.assertEqual(db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 0)
        db.close()

    def test_installer_all_agents(self):
        with tempfile.TemporaryDirectory() as dir_name:
            target = Path(dir_name) / "study"
            created = installer.install(target, "all")
            self.assertEqual(len(created), 11)
            for path in (target / ".agents/skills/taiwan-tutor/SKILL.md",
                         target / ".claude/skills/taiwan-question-designer/SKILL.md",
                         target / ".taiwan-learning/tools/learning_cli.py",
                         target / ".taiwan-learning/references/sources.json"):
                self.assertTrue(path.exists(), str(path))
            with self.assertRaises(RuntimeError):
                installer.install(target, "all")
            # Reinstall over the skills, never touch learner data.
            data_dir = target / ".taiwan-learning-data"
            data_dir.mkdir()
            (data_dir / "keep.txt").write_text("private", encoding="utf-8")
            installer.install(target, "all", force=True)
            self.assertEqual((data_dir / "keep.txt").read_text(encoding="utf-8"), "private")


if __name__ == "__main__":
    unittest.main()
