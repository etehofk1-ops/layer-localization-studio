import importlib.util
import json
import os
from pathlib import Path
import subprocess
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

    def directory_link(self, link, target):
        # All fixture paths, including junction targets, stay inside this test's temp root.
        self.assertTrue(link.resolve().is_relative_to(self.root.resolve()))
        self.assertTrue(target.resolve().is_relative_to(self.root.resolve()))
        if os.name == "nt":
            env = dict(os.environ, LAYER_TEST_LINK=str(link), LAYER_TEST_TARGET=str(target))
            subprocess.run([
                "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                "$ErrorActionPreference='Stop'; New-Item -ItemType Junction "
                "-Path $env:LAYER_TEST_LINK -Target $env:LAYER_TEST_TARGET | Out-Null",
            ], env=env, check=True, capture_output=True)
            self.addCleanup(os.rmdir, link)
        else:
            link.symlink_to(target, target_is_directory=True)
            self.addCleanup(link.unlink)
        self.assertEqual(link.resolve(), target.resolve())

    def test_persisted_asset_id_is_rejected_before_any_output(self):
        output, job = self.fixture()
        metadata = read(job / "job.json")
        spec = read(output / "spec.json")
        spec["revision"] = "v002"
        self.rewrite(output / "spec.json", spec)
        for invalid in ("../escaped", str(self.root / "absolute"), "C:\\escape", "CON", "", None):
            with self.subTest(asset_id=invalid):
                metadata["asset_id"] = invalid
                self.rewrite(job / "job.json", metadata)
                before = set(self.root.rglob("*"))
                with self.assertRaisesRegex(ValueError, "identifier|Reserved Windows"):
                    build(job, output / "spec.json")
                self.assertEqual(set(self.root.rglob("*")), before)
                with self.assertRaisesRegex(ValueError, "identifier|Reserved Windows"):
                    verify(job, "v001")
                with self.assertRaisesRegex(ValueError, "identifier|Reserved Windows"):
                    archive_attempt(job, output / "record-0.json")

    def test_archive_rejects_outward_generation_directory_link(self):
        output, job = self.fixture()
        link = job / "작업기록" / "generations"
        target = self.root / "outside-generations"
        link.rename(target)
        self.directory_link(link, target)
        record = read(output / "record-0.json")
        record["id"] = "new-attempt"
        self.rewrite(output / "new-record.json", record)
        before = set(target.rglob("*"))
        with self.assertRaisesRegex(ValueError, "leaves"):
            archive_attempt(job, output / "new-record.json")
        self.assertEqual(set(target.rglob("*")), before)

    def test_build_preflights_all_outward_output_directory_links(self):
        for index, relative in enumerate(("레이어에셋", "통합에셋", "작업기록/builds")):
            with self.subTest(parent=relative):
                output = self.root / f"fixture-{index}"
                demo_module.demo(output)
                job = output / "demo-job"
                link, target = job / relative, self.root / f"outside-{index}"
                link.rename(target)
                self.directory_link(link, target)
                spec = read(output / "spec.json")
                spec["revision"] = "v002"
                self.rewrite(output / "spec.json", spec)
                before = set(self.root.rglob("*"))
                with self.assertRaisesRegex(ValueError, "leaves"):
                    build(job, output / "spec.json")
                self.assertEqual(set(self.root.rglob("*")), before)

    def test_verify_rejects_outward_build_record_directory_link(self):
        _, job = self.fixture()
        link, target = job / "작업기록" / "builds" / "v001", self.root / "outside-record"
        link.rename(target)
        self.directory_link(link, target)
        with self.assertRaisesRegex(ValueError, "leaves"):
            verify(job, "v001")

    def test_build_rejects_dangling_outward_psd_link(self):
        output, job = self.fixture()
        link, target = job / "synthetic-v002.psd", self.root / "outside.psd"
        try:
            link.symlink_to(target)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows account cannot create file symlinks; directory junction cases still run.")
            raise
        self.addCleanup(link.unlink)
        spec = read(output / "spec.json")
        spec["revision"] = "v002"
        self.rewrite(output / "spec.json", spec)
        before = set(self.root.rglob("*"))
        with self.assertRaisesRegex(ValueError, "leaves"):
            build(job, output / "spec.json")
        self.assertFalse(target.exists())
        self.assertEqual(set(self.root.rglob("*")), before)

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
