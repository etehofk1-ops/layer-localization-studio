import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from layer_studio.core import archive_attempt, build, init_job, inside, read, sha, stats, verify
from layer_studio.cli import main

module_spec = importlib.util.spec_from_file_location("demo", Path(__file__).parents[1] / "examples" / "demo.py")
demo_module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(demo_module)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self):
        output = self.root / "fixture"
        demo_module.demo(output)
        return output, output / "demo-job"

    def rewrite(self, path, data):
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_end_to_end_source_order_opacity_hidden_layer_and_no_approval(self):
        output, job = self.fixture()
        self.assertEqual(sha(output / "source.png"), sha(job / "원본에셋" / "source.png"))
        qa = read(job / "작업기록" / "builds" / "v001" / "qa.json")
        self.assertEqual(qa["psd"]["panel_top_to_bottom"], ["검사 레이어 2", "검사 레이어 1", "검사 레이어 0"])
        self.assertEqual(qa["generation_calls"], 0)
        self.assertEqual(qa["test_fixture_records"], 3)
        self.assertEqual(qa["visual_review"], "PENDING")
        self.assertFalse(verify(job, "v001")["release_approved"])
        self.assertFalse(list(job.rglob("*.zip")))

    def test_transparent_rgb_is_excluded_from_color_measurements(self):
        im = Image.new("RGBA", (3, 1))
        im.putdata([(255, 0, 255, 0), (0, 50, 100, 255), (250, 240, 230, 128)])
        measured = stats(im)
        self.assertEqual(measured["frequent_opaque_colors"], [{"rgb": [0, 50, 100], "count": 1}])
        self.assertEqual(measured["transparent_fraction"], 1 / 3)

    def test_revisions_and_attempts_cannot_overwrite(self):
        output, job = self.fixture()
        before = sha(job / "synthetic-v001.psd")
        with self.assertRaises(ValueError):
            build(job, output / "spec.json")
        with self.assertRaises(FileExistsError):
            archive_attempt(job, output / "record-0.json")
        self.assertEqual(sha(job / "synthetic-v001.psd"), before)

    def test_changed_original_blocks_build(self):
        output, job = self.fixture()
        (job / "원본에셋" / "source.png").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "original changed"):
            build(job, output / "spec.json")

    def test_changed_raw_generation_blocks_build(self):
        output, job = self.fixture()
        raw = job / "작업기록" / "generations" / "fixture-0" / "raw.png"
        raw.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "generation evidence"):
            build(job, output / "spec.json")

    def test_manifest_detects_changed_layer(self):
        _, job = self.fixture()
        path = job / "레이어에셋" / "v001" / "L0_fixture.png"
        path.write_bytes(path.read_bytes() + b"extra")
        with self.assertRaisesRegex(ValueError, "Changed file"):
            verify(job, "v001")

    def test_analysis_must_precede_archiving(self):
        output, job = self.fixture()
        fresh = output / "unreviewed-job"
        init_job(output / "source.png", fresh, "unreviewed", "ko")
        with self.assertRaisesRegex(ValueError, "source analysis"):
            archive_attempt(fresh, output / "record-0.json")

    def test_rejected_attempt_retained_but_not_composited(self):
        output, job = self.fixture()
        record = read(output / "record-0.json")
        record.update({"id": "rejected-1", "outcome": "rejected", "retry_of": "fixture-0"})
        self.rewrite(output / "rejected.json", record)
        archive_attempt(job, output / "rejected.json")
        spec = read(output / "spec.json")
        spec["revision"] = "v002"
        spec["layers_bottom_to_top"][0]["generation_ids"] = ["rejected-1"]
        self.rewrite(output / "rejected-spec.json", spec)
        with self.assertRaisesRegex(ValueError, "Rejected"):
            build(job, output / "rejected-spec.json")
        self.assertTrue((job / "작업기록" / "generations" / "rejected-1" / "raw.png").is_file())

    def test_wrong_canvas_and_blend_fail_before_output_creation(self):
        output, job = self.fixture()
        spec = read(output / "spec.json")
        spec["revision"] = "v002"
        Image.new("RGBA", (12, 15)).save(output / "wrong.png")
        spec["layers_bottom_to_top"][0]["file"] = "wrong.png"
        self.rewrite(output / "wrong-spec.json", spec)
        with self.assertRaisesRegex(ValueError, "full canvas"):
            build(job, output / "wrong-spec.json")
        self.assertFalse((job / "통합에셋" / "v002").exists())
        spec["layers_bottom_to_top"][0]["blend_mode"] = "multiply"
        self.rewrite(output / "wrong-spec.json", spec)
        with self.assertRaisesRegex(ValueError, "normal blending"):
            build(job, output / "wrong-spec.json")

    def test_original_cannot_be_registered_as_generated(self):
        output, job = self.fixture()
        record = read(output / "record-0.json")
        record.update({"id": "bad-source", "output": "source.png"})
        self.rewrite(output / "bad-record.json", record)
        with self.assertRaisesRegex(ValueError, "Original bytes"):
            archive_attempt(job, output / "bad-record.json")

    def test_manifest_path_cannot_escape_job(self):
        with self.assertRaisesRegex(ValueError, "leaves"):
            inside(self.root, "../elsewhere.txt")

    def test_recipe_code_is_archived_without_execution(self):
        output, job = self.fixture()
        recipe = output / "recipe.py"
        recipe.write_text("raise RuntimeError('Must only be archived, never executed')\n", encoding="utf-8")
        spec = read(output / "spec.json")
        spec.update({"revision": "v002", "processing_files": ["recipe.py"]})
        self.rewrite(output / "recipe-spec.json", spec)
        build(job, output / "recipe-spec.json")
        snapshot = read(job / "작업기록" / "builds" / "v002" / "spec.json")
        self.assertEqual(sha(job / snapshot["processing_files"][0]["file"]), sha(recipe))
        self.assertEqual(verify(job, "v001")["structural_status"], "PASS")
        self.assertEqual(verify(job, "v002")["structural_status"], "PASS")

    def test_cli_failed_verification_returns_nonzero(self):
        self.assertEqual(main(["verify", str(self.root / "absent"), "v001"]), 1)


if __name__ == "__main__":
    unittest.main()
