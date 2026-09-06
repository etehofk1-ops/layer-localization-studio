"""Preserve source bytes, archive attempts, export and verify layered candidates."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

from PIL import Image, ImageChops, ImageStat
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
from psd_tools.constants import BlendMode

ORIGINAL = "원본에셋"
LAYERS = "레이어에셋"
COMPOSITES = "통합에셋"
RECORDS = "작업기록"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value),
            "Use a 1-64 character ASCII identifier (letters, digits, underscore, hyphen).")
    require(value.upper().split(".")[0] not in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(10)], *[f"LPT{i}" for i in range(10)]},
            "Reserved Windows filename.")
    return value


def inside(root, relative):
    require(isinstance(relative, str) and bool(relative), "Missing relative path.")
    path = (Path(root) / relative).resolve()
    require(path.is_relative_to(Path(root).resolve()), "Path leaves the job folder.")
    return path


def png(path):
    with Image.open(path) as opened:
        require(opened.format == "PNG" and not getattr(opened, "is_animated", False), "Use a single-frame PNG.")
        require(max(opened.size) <= 30000, "PSD canvas must be at most 30000 px per side.")
        return opened.convert("RGBA")


def stats(im):
    alpha = im.getchannel("A")
    hist = alpha.histogram()
    total = im.width * im.height
    # Opaque colors describe cores; translucent pixels are not mixed into them.
    colors = Counter((r, g, b) for r, g, b, a in im.get_flattened_data() if a >= 240)
    return {
        "size_px": list(im.size), "alpha_bbox_px": alpha.getbbox(),
        "transparent_fraction": hist[0] / total,
        "semitransparent_fraction": sum(hist[1:255]) / total,
        "opaque_fraction": hist[255] / total,
        "frequent_opaque_colors": [{"rgb": list(c), "count": n} for c, n in colors.most_common(8)],
        "color_note": "Whole-image opaque samples only; measure each visual layer separately.",
    }


def on_background(im, color):
    base = Image.new("RGBA", im.size, (*color, 255))
    return Image.alpha_composite(base, im).convert("RGB")


def init_job(source, job, asset_id, locale):
    source, job = Path(source).resolve(), Path(job).resolve()
    identifier(asset_id)
    identifier(locale)
    im = png(source)
    require(not job.exists(), "Job already exists; choose a new job/version.")
    for directory in (ORIGINAL, LAYERS, COMPOSITES, RECORDS):
        (job / directory).mkdir(parents=True)
    original = job / ORIGINAL / "source.png"
    shutil.copyfile(source, original)
    metadata = {"schema_version": 1, "asset_id": asset_id, "locale": locale,
                "source": {"file": f"{ORIGINAL}/source.png", "sha256": sha(original), "size_px": list(im.size)},
                "created_at": stamp()}
    write_new(job / "job.json", metadata)
    analysis = {"measurements": stats(im), "translation": {"text": "", "source": ""},
                "reviewed_by": "", "viewed_on_dark_and_light": False,
                "layers_bottom_to_top": [], "planned_generation_calls": None,
                "unresolved_observations": [], "source_pixel_cutout_allowed": False,
                "source_alpha_inheritance_allowed": False}
    write_new(job / RECORDS / "analysis.json", analysis)
    for label, color in (("dark", (20, 20, 24)), ("light", (233, 232, 228))):
        on_background(im, color).save(job / RECORDS / f"source-{label}.png")
    return metadata


def source_checked(job):
    metadata = read(Path(job) / "job.json")
    source = inside(job, metadata["source"]["file"])
    require(sha(source) == metadata["source"]["sha256"], "Archived original changed.")
    return metadata, source


def analysis_checked(job):
    analysis = read(Path(job) / RECORDS / "analysis.json")
    require(bool(analysis.get("reviewed_by", "").strip()) and analysis.get("viewed_on_dark_and_light") is True,
            "Finish the source analysis and record the reviewer first.")
    translation = analysis.get("translation", {})
    require(all(isinstance(translation.get(k), str) and translation[k].strip() for k in ("text", "source")),
            "Record the exact translation and its source.")
    planned = analysis.get("planned_generation_calls")
    require(type(planned) is int and planned >= 0, "Record a nonnegative planned generation count.")
    require(bool(analysis.get("layers_bottom_to_top")), "Record the inferred layer stack.")
    for layer in analysis["layers_bottom_to_top"]:
        require(all(layer.get(k) for k in ("name", "role", "evidence", "action")), "Layer analysis needs name, role, evidence, action.")
    require(analysis.get("source_pixel_cutout_allowed") is False and analysis.get("source_alpha_inheritance_allowed") is False,
            "This workflow does not permit source cutouts or source alpha inheritance.")
    return analysis


def archive_attempt(job, record_file):
    job, record_file = Path(job).resolve(), Path(record_file).resolve()
    metadata, _ = source_checked(job)
    analysis = analysis_checked(job)
    record = read(record_file)
    attempt = identifier(record["id"])
    for key in ("backend", "prompt", "outcome", "output"):
        require(isinstance(record.get(key), str) and record[key].strip(), f"Missing attempt {key}.")
    require(record["outcome"] in ("candidate", "rejected"), "Archive outcome must be candidate or rejected.")
    require(record.get("kind") in ("generation", "test_fixture"), "Record kind: generation or test_fixture.")
    root = job / RECORDS / "generations"
    existing = list(root.glob("*/record.json")) if root.exists() else []
    parent = record.get("retry_of")
    if parent:
        identifier(parent)
        require((root / parent / "record.json").is_file(), "Retry must reference an archived attempt.")
    raw = (record_file.parent / record["output"]).resolve()
    png(raw)
    require(sha(raw) != metadata["source"]["sha256"], "Original bytes cannot be registered as generated output.")
    references = [(record_file.parent / p).resolve() for p in record.get("references", [])]
    for reference in references:
        png(reference)
    destination = root / attempt
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(raw, destination / "raw.png")
    refs = []
    for index, reference in enumerate(references):
        name = f"reference-{index + 1:02d}.png"
        shutil.copyfile(reference, destination / name)
        refs.append({"file": name, "sha256": sha(destination / name)})
    archived = {"id": attempt, "sequence": len(existing) + 1, "kind": record["kind"],
                "backend": record["backend"], "prompt": record["prompt"], "outcome": record["outcome"],
                "retry_of": parent, "notes": record.get("notes", ""), "recorded_at": stamp(),
                "raw": {"file": "raw.png", "sha256": sha(destination / "raw.png")}, "references": refs,
                "analysis_sha256": sha(job / RECORDS / "analysis.json")}
    write_new(destination / "analysis.json", analysis)
    archived["analysis_sha256"] = sha(destination / "analysis.json")
    write_new(destination / "record.json", archived)
    return archived


def attempt_checked(job, attempt):
    base = Path(job) / RECORDS / "generations" / identifier(attempt)
    record = read(base / "record.json")
    require(sha(base / "analysis.json") == record["analysis_sha256"], "Changed analysis snapshot.")
    for item in [record["raw"], *record["references"]]:
        require(sha(inside(base, item["file"])) == item["sha256"], f"Changed generation evidence: {attempt}.")
    return record


def delta(a, b):
    require(a.size == b.size, "Image sizes differ.")
    diff = ImageChops.difference(a, b)
    extrema = diff.getextrema()
    maximum = extrema[1] if len(diff.getbands()) == 1 else max(high for _, high in extrema)
    return {"max_channel_delta": maximum,
            "mean_channel_delta": sum(ImageStat.Stat(diff).mean) / len(diff.getbands())}


def check_psd(path, expected, layers):
    doc = PSDImage.open(path)
    require(doc.size == expected.size and len(doc) == len(layers), "PSD size or layer count mismatch.")
    pixel_checks = []
    for actual, wanted in zip(doc, layers):
        require(actual.name == wanted["name"] and actual.opacity == wanted["opacity"]
                and actual.visible == wanted["visible"] and actual.blend_mode == BlendMode.NORMAL
                and actual.bbox == (0, 0, *expected.size), "PSD layer metadata mismatch.")
        saved = actual.topil().convert("RGBA")
        prepared = png(inside(Path(path).parent, wanted["file"]))
        alpha_check = delta(saved.getchannel("A"), prepared.getchannel("A"))
        require(alpha_check["max_channel_delta"] == 0, "PSD layer alpha changed.")
        for color in ((20, 20, 24), (233, 232, 228)):
            require(delta(on_background(saved, color), on_background(prepared, color))["max_channel_delta"] <= 1,
                    "PSD layer pixels changed.")
        pixel_checks.append({"name": actual.name, "raster_pixels": "PASS", "alpha": "EXACT"})
    rendered = doc.composite(force=True, apply_icc=False).convert("RGBA")
    checks = {}
    for label, color in (("dark", (20, 20, 24)), ("light", (233, 232, 228))):
        checks[label] = delta(on_background(rendered, color), on_background(expected, color))
        require(checks[label]["max_channel_delta"] <= 3 and checks[label]["mean_channel_delta"] <= 0.5,
                f"PSD composite differs on {label} background: {checks[label]}")
    checks["alpha"] = delta(rendered.getchannel("A"), expected.getchannel("A"))
    require(checks["alpha"]["max_channel_delta"] <= 3, "PSD alpha differs.")
    return {"status": "PASS", "layer_count": len(doc), "comparisons": checks,
            "layers": pixel_checks,
            "panel_top_to_bottom": [layer.name for layer in reversed(list(doc))],
            "reader": "psd-tools", "photoshop_gui_opened": False}


def build(job, spec_file):
    job, spec_file = Path(job).resolve(), Path(spec_file).resolve()
    metadata, source = source_checked(job)
    analysis = analysis_checked(job)
    spec = read(spec_file)
    revision = identifier(spec["revision"])
    require(spec.get("source_pixels_used") is False and spec.get("source_alpha_copied") is False,
            "Declare the source-pixel and source-alpha boundaries explicitly.")
    size = tuple(metadata["source"]["size_px"])
    recipes = [(spec_file.parent / p).resolve() for p in spec.get("processing_files", [])]
    for recipe in recipes:
        require(recipe.is_file(), "Missing processing recipe file.")
    layers = spec.get("layers_bottom_to_top", [])
    require(bool(layers), "Build requires at least one layer.")
    inputs, ids, attempts = [], set(), set()
    for layer in layers:
        name = identifier(layer["id"])
        require(name.lower() not in ids, "Duplicate layer ID.")
        ids.add(name.lower())
        require(isinstance(layer.get("name"), str) and layer["name"].strip() and len(layer["name"]) < 256
                and "\x00" not in layer["name"], "Invalid layer name (maximum 255 characters).")
        require(layer.get("blend_mode", "normal") == "normal", "Only normal blending is supported; bake effects first.")
        require(type(layer.get("opacity", 255)) is int and 0 <= layer.get("opacity", 255) <= 255, "Opacity must be 0..255.")
        require(type(layer.get("visible", True)) is bool, "Visibility must be boolean.")
        require(isinstance(layer.get("processing"), list) and bool(layer["processing"]), "Record placement/effects or an explicit no-processing note.")
        require(bool(layer.get("generation_ids")), "Layer needs archived generation provenance.")
        for attempt in layer["generation_ids"]:
            record = attempt_checked(job, attempt)
            require(record["outcome"] != "rejected", "Rejected attempts cannot supply final layer pixels.")
            attempts.add(attempt)
        path = (spec_file.parent / layer["file"]).resolve()
        im = png(path)
        require(im.size == size, "Layers must already be placed on the original-size full canvas.")
        require(sha(path) != metadata["source"]["sha256"], "Do not use the original file as a generated layer.")
        inputs.append((path, im))
    destination = job / COMPOSITES / revision
    layer_dir = job / LAYERS / revision
    record_dir = job / RECORDS / "builds" / revision
    psd_path = job / f"{metadata['asset_id']}-{revision}.psd"
    for path in (destination, layer_dir, record_dir, psd_path):
        require(not path.exists(), "Revision already exists, including partial builds; choose a new revision.")
    for directory in (destination, layer_dir, record_dir):
        directory.mkdir(parents=True)
    write_new(record_dir / "analysis.json", analysis)
    archived_recipes = []
    for index, recipe in enumerate(recipes):
        recipe_dir = record_dir / "recipes"
        recipe_dir.mkdir(exist_ok=True)
        destination_recipe = recipe_dir / f"{index + 1:02d}-{recipe.name}"
        shutil.copyfile(recipe, destination_recipe)
        archived_recipes.append({"file": destination_recipe.relative_to(job).as_posix(), "sha256": sha(destination_recipe)})
    merged = Image.new("RGBA", size)
    doc = PSDImage.new("RGBA", size, color=(0, 0, 0, 0))
    archived_layers = []
    for layer, (path, im) in zip(layers, inputs):
        filename = f"{layer['id']}.png"
        shutil.copyfile(path, layer_dir / filename)
        opacity, visible = layer.get("opacity", 255), layer.get("visible", True)
        pixel = PixelLayer.frompil(im, doc, name=layer["id"])
        # Setter writes the Unicode name tag and a safe legacy Pascal name.
        pixel.name = layer["name"]
        pixel.opacity, pixel.visible = opacity, visible
        prepared = im.copy()
        prepared.putalpha(prepared.getchannel("A").point(lambda v: round(v * opacity / 255)))
        if visible:
            merged = Image.alpha_composite(merged, prepared)
        archived_layers.append({**layer, "file": (layer_dir / filename).relative_to(job).as_posix(),
                                "sha256": sha(layer_dir / filename), "opacity": opacity,
                                "visible": visible, "blend_mode": "normal"})
    merged.save(destination / "candidate.png")
    doc.save(psd_path)
    normalized = {"revision": revision, "layers_bottom_to_top": archived_layers,
                  "processing_files": archived_recipes,
                  "source_pixels_used": False, "source_alpha_copied": False}
    write_new(record_dir / "spec.json", normalized)
    psd_qa = check_psd(psd_path, merged, archived_layers)
    for label, color in (("dark", (20, 20, 24)), ("light", (233, 232, 228))):
        sheet = Image.new("RGB", (size[0] * 2, size[1]))
        sheet.paste(on_background(png(source), color), (0, 0))
        sheet.paste(on_background(merged, color), (size[0], 0))
        sheet.save(destination / f"source-candidate-{label}.png")
    all_records = [attempt_checked(job, p.parent.name) for p in (job / RECORDS / "generations").glob("*/record.json")]
    real = [r for r in all_records if r["kind"] == "generation"]
    qa = {"status": "CANDIDATE", "executed": True, "structural_status": "PASS", "psd": psd_qa,
          "generation_calls": len(real), "retry_calls": sum(bool(r["retry_of"]) for r in real),
          "test_fixture_records": len(all_records) - len(real), "used_attempts": sorted(attempts),
          "planned_generation_calls": analysis["planned_generation_calls"],
          "visual_review": "PENDING", "fidelity_review": "PENDING", "in_game_qa": "NOT_RUN",
          "release_approved": False, "source_pixel_policy": "DECLARED_BY_OPERATOR_NOT_PROVEN_BY_HASH",
          "created_at": stamp()}
    write_new(record_dir / "qa.json", qa)
    files = [job / "job.json", source, psd_path]
    for directory in (destination, layer_dir, record_dir, job / RECORDS / "generations"):
        files.extend(p for p in directory.rglob("*") if p.is_file())
    write_new(record_dir / "manifest.json", {"revision": revision, "algorithm": "sha256",
              "excludes_itself": True, "files": [{"file": p.relative_to(job).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size}
                                                for p in sorted(set(files))]})
    return qa


def verify(job, revision):
    job = Path(job).resolve()
    metadata, _ = source_checked(job)
    identifier(revision)
    record_dir = job / RECORDS / "builds" / revision
    manifest = read(record_dir / "manifest.json")
    require(bool(manifest.get("files")), "Empty manifest.")
    for item in manifest["files"]:
        path = inside(job, item["file"])
        require(path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], f"Changed file: {item['file']}")
    layers = read(record_dir / "spec.json")["layers_bottom_to_top"]
    result = check_psd(job / f"{metadata['asset_id']}-{revision}.psd", png(job / COMPOSITES / revision / "candidate.png"), layers)
    return {"structural_status": "PASS", "verified_files": len(manifest["files"]), "psd": result,
            "release_approved": False, "note": "Integrity and PSD checks do not approve visual fidelity or game integration."}
