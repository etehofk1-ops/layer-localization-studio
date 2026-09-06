"""Synthetic archive/PSD demonstration, NOT a localization or generation example."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
from layer_studio.core import archive_attempt, build, init_job, read, verify, write_new


def demo(destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    size = (160, 96)
    source = Image.new("RGBA", size)
    ImageDraw.Draw(source).rounded_rectangle((6, 6, 153, 89), 14, fill=(36, 58, 89, 255))
    source.save(destination / "source.png")
    job = destination / "demo-job"
    init_job(destination / "source.png", job, "synthetic", "ko")
    analysis = read(job / "작업기록" / "analysis.json")
    analysis.update({"translation": {"text": "합성 검사", "source": "Synthetic test label; no lettering generated"},
                     "reviewed_by": "synthetic fixture setup", "viewed_on_dark_and_light": True,
                     "planned_generation_calls": 0,
                     "layers_bottom_to_top": [{"name": "panel", "role": "art", "evidence": "Known synthetic rounded rectangle", "action": "test_fixture"},
                                               {"name": "overlay", "role": "effect", "evidence": "Known synthetic translucent rectangle", "action": "test_fixture"}]})
    (job / "작업기록" / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    layers = []
    for number, color in enumerate(((44, 70, 110, 255), (241, 152, 71, 137), (90, 230, 130, 200))):
        im = Image.new("RGBA", size)
        ImageDraw.Draw(im).rectangle((10 + number * 20, 10 + number * 10, 135, 78), fill=color)
        im.save(destination / f"layer-{number}.png")
        record = {"id": f"fixture-{number}", "kind": "test_fixture", "backend": "local synthetic fixture",
                  "prompt": "No AI call: deterministic shapes for archive/PSD tests only.",
                  "outcome": "candidate", "output": f"layer-{number}.png", "references": ["source.png"], "retry_of": None}
        write_new(destination / f"record-{number}.json", record)
        archive_attempt(job, destination / f"record-{number}.json")
        layers.append({"id": f"L{number}_fixture", "name": f"검사 레이어 {number}", "file": f"layer-{number}.png",
                       "opacity": 191 if number == 1 else 255, "visible": number != 2, "blend_mode": "normal",
                       "generation_ids": [f"fixture-{number}"], "processing": ["Synthetic full-canvas test; no source pixels used."]})
    spec = {"revision": "v001", "source_pixels_used": False, "source_alpha_copied": False, "layers_bottom_to_top": layers}
    write_new(destination / "spec.json", spec)
    build(job, destination / "spec.json")
    return {"job": str(job), "verification": verify(job, "v001")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", help="A new directory, normally under jobs/")
    print(json.dumps(demo(parser.parse_args().destination), ensure_ascii=False, indent=2))
