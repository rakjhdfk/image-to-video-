"""Align the per-second editorial timeline to recorded dialogue clip intervals.

The screenplay remains the planning source. This module only updates generated
timeline dialogue annotations and their timing metadata; it does not change
locations, action, camera, effects, music or the screenplay itself.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
from pathlib import Path
import tempfile


VOICE_FIELDS = {"dialogue_or_narration", "actual_dialogue_timing"}


def _line_key(shot, line):
    return (int(shot), line["speaker"], line["text"])


def sync_timeline(outdir) -> dict:
    """Retain planning metadata while annotating actual speech in each second.

    Reads episode01_timeline.json and voices/dialogue_manifest.json. When the
    original screenplay exists, its dialogue offsets/durations are retained as
    planned_offset/planned_duration. Existing planning metadata is also reused,
    so calling this repeatedly never turns actual durations into planned ones.
    Clip intervals are left-closed/right-open; this is clip alignment, not
    forced word or phoneme alignment. The update is atomic and idempotent.
    """
    outdir = Path(outdir)
    path = outdir / "episode01_timeline.json"
    original_text = path.read_text(encoding="utf-8")
    rows = json.loads(original_text)
    voices = json.loads((outdir / "voices" / "dialogue_manifest.json").read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) != 600:
        raise ValueError("Expected the complete 600-row episode timeline.")
    if not isinstance(voices, list) or not voices:
        raise ValueError("Actual dialogue manifest is empty or invalid.")
    for second, row in enumerate(rows):
        if (row.get("second"), row.get("start"), row.get("end")) != (second, second, second + 1):
            raise ValueError(f"Timeline is not contiguous at second {second}.")

    # Preserve every field unrelated to voice annotations.
    preserved = [{k: copy.deepcopy(v) for k, v in row.items() if k not in VOICE_FIELDS} for row in rows]
    planned = {}
    existing = {}
    for row in rows:
        for line in row.get("dialogue_or_narration", []):
            key = _line_key(row["shot_id"], line)
            existing.setdefault(key, copy.deepcopy(line))
            planned.setdefault(key, {
                "offset": line.get("planned_offset", line.get("offset")),
                "duration": line.get("planned_duration", line.get("duration")),
            })
    screenplay_path = outdir / "episode01_screenplay.json"
    if screenplay_path.exists():
        screenplay = json.loads(screenplay_path.read_text(encoding="utf-8"))
        for shot in screenplay["shots"]:
            for line in shot.get("dialogue", []):
                key = _line_key(shot["id"], line)
                planned[key] = {"offset": line.get("offset"), "duration": line.get("duration")}
                existing.setdefault(key, copy.deepcopy(line))

    shot_bounds = {}
    for row in rows:
        bounds = shot_bounds.setdefault(int(row["shot_id"]), [row["start"], row["end"]])
        bounds[0] = min(bounds[0], row["start"])
        bounds[1] = max(bounds[1], row["end"])
    by_shot = {}
    for index, voice in enumerate(voices):
        shot_id = int(voice["shot"])
        start, end = float(voice["start"]), float(voice["end"])
        if shot_id not in shot_bounds or not math.isfinite(start) or not math.isfinite(end):
            raise ValueError(f"Invalid shot or timing for dialogue clip {index}.")
        lower, upper = shot_bounds[shot_id]
        if not lower <= start < end <= upper + 1e-7:
            raise ValueError(f"Dialogue clip {index} lies outside its shot.")
        if not voice.get("speaker") or not voice.get("text") or not voice.get("file"):
            raise ValueError(f"Dialogue clip {index} lacks its actual recording metadata.")
        by_shot.setdefault(shot_id, []).append(voice)
    for group in by_shot.values():
        group.sort(key=lambda line: (line["start"], line["end"], line["speaker"]))

    seconds_with_speech = annotations = 0
    for row in rows:
        second, shot_id = row["second"], int(row["shot_id"])
        shot_start = shot_bounds[shot_id][0]
        active = []
        for voice in by_shot.get(shot_id, []):
            if max(voice["start"], second) >= min(voice["end"], second + 1):
                continue
            key = _line_key(shot_id, voice)
            estimate = planned.get(key, {})
            annotation = copy.deepcopy(existing.get(key, {}))
            annotation.update({
                "speaker": voice["speaker"],
                "text": voice["text"],
                "offset": voice["start"] - shot_start,
                "duration": voice["end"] - voice["start"],
                "actual_start_seconds": voice["start"],
                "actual_end_seconds": voice["end"],
                "voice_file": voice["file"],
                "planned_offset": estimate.get("offset"),
                "planned_duration": estimate.get("duration"),
                "timing_source": "voices/dialogue_manifest.json",
            })
            active.append(annotation)
        row["dialogue_or_narration"] = active
        row["actual_dialogue_timing"] = {
            "reference": "voices/dialogue_manifest.json",
            "speech_active_in_this_second": bool(active),
            "accuracy": "WAV-duration aligned; clip intervals, not word-level forced alignment",
        }
        seconds_with_speech += bool(active)
        annotations += len(active)

    if preserved != [{k: v for k, v in row.items() if k not in VOICE_FIELDS} for row in rows]:
        raise RuntimeError("Refusing to change non-dialogue timeline fields.")
    encoded = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    changed = encoded != original_text
    if changed:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=outdir, prefix=".timeline-sync-", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return {
        "timeline_rows": len(rows),
        "voice_clips": len(voices),
        "seconds_with_speech": seconds_with_speech,
        "dialogue_annotations": annotations,
        "changed": changed,
        "timing_source": "voices/dialogue_manifest.json",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outdir", nargs="?", default=str(Path(__file__).resolve().parent / "output"))
    print(json.dumps(sync_timeline(parser.parse_args().outdir), indent=2))
