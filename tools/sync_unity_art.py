"""Copy approved source atlases into Unity without resampling or recolouring.

Run from any directory with Python 3. No third-party packages are required.
Existing clip IDs are retained so Animator parameters remain stable after refresh.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "unity/Alisa2D"
DEST = PROJECT / "Assets/Alisa/Art"
MANIFEST = DEST / "AlisaSources.json"

LABELS = {
    "key_poses_back": "Спина — четыре опорные позы",
    "walk_back": "Спина — ходьба",
    "idle_back": "Спина — idle",
    "idle_side_right": "Бок вправо — idle",
    "walk_side_right": "Бок вправо — ходьба",
    "idle_side_left": "Бок влево — idle",
    "walk_side_left": "Бок влево — ходьба",
    "idle_left": "Передняя левая диагональ — idle",
    "start_left": "Передняя левая диагональ — старт",
    "walk_left": "Передняя левая диагональ — ходьба",
    "stop_left": "Передняя левая диагональ — остановка",
    "turn_left_right": "Передний ракурс — смена стороны",
    "idle_right": "Передняя правая диагональ — idle",
    "start_right": "Передняя правая диагональ — старт",
    "walk_right": "Передняя правая диагональ — ходьба",
    "stop_right": "Передняя правая диагональ — остановка",
    "dance_original": "Исходный танец — голубые глаза",
}


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", header[16:24])


def copy_if_changed(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_bytes() != source.read_bytes():
        shutil.copyfile(source, target)


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    previous = json.loads(MANIFEST.read_text("utf-8")) if MANIFEST.exists() else {}
    ids = {item["key"]: item["id"] for item in previous.get("clips", [])}
    next_id = max(ids.values(), default=0) + 1
    atlases, clips = [], []

    def add_clip(key, label, group, atlas_key, frames, durations, loop, historical=False, note=""):
        nonlocal next_id
        if key not in ids:
            ids[key] = next_id
            next_id += 1
        assert len(frames) == len(durations) and frames
        assert all(value > 0 and value % 10 == 0 for value in durations), key
        clips.append(dict(id=ids[key], key=key, label=label, group=group,
                          atlasKey=atlas_key, frames=frames, durationsMs=durations,
                          loop=loop, historical=historical, note=note))

    def add_atlas(key, source, frames):
        source = ROOT / source
        width, height = png_size(source)
        target = DEST / key / source.name
        copy_if_changed(source, target)
        for frame in frames:
            assert frame["w"] == 36 and frame["h"] == 86, (key, frame)
            assert 0 <= frame["x"] <= width - 36 and 0 <= frame["y"] <= height - 86
        atlases.append(dict(key=key, assetPath=target.relative_to(PROJECT).as_posix(),
                            source=source.relative_to(ROOT).as_posix(),
                            sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                            width=width, height=height, frames=frames))

    packs = [
        ("RearRedraw", "alisa/rear_key_redraw/Alisa_rear_redrawn.json", "01 Спина — новая основа", False),
        ("Side", "alisa/side_walk/Alisa_side.json", "02 Боковые ракурсы", False),
        ("Front", "alisa/motion_next/Alisa_motion_next.json", "03 Передние диагонали и танец", False),
        ("RearArchive", "alisa/back_walk/Alisa_back.json", "Архив — спина, первая версия", True),
        ("RearPolishedArchive", "alisa/back_walk_polished/Alisa_back_polished.json", "Архив — спина, предыдущая версия", True),
    ]
    front_data = None
    for key, json_path, group, historical in packs:
        path = ROOT / json_path
        data = json.loads(path.read_text("utf-8"))
        frames = []
        for item in data["frames"]:
            frames.append(dict(**item["frame"], pivotX=18, pivotY=85))
        for tag in data["meta"]["frameTags"]:
            indices = list(range(tag["from"], tag["to"] + 1))
            assert tag["direction"] == "forward", tag
            pivot = tag.get("pivot", {"x": 18, "y": 85})
            for index in indices:
                frames[index].update(pivotX=pivot["x"], pivotY=pivot["y"])
            note = ""
            if historical:
                note = "Предыдущий эксперимент. Клип показан на месте, без записанного перемещения по сцене."
            elif key == "RearRedraw":
                note = "Новая задняя основа: 36×86, восемь кадров по 120 мс. Проверка на месте."
            add_clip(f"{key}/{tag['name']}", LABELS.get(tag["name"], tag["name"]), group,
                     key, indices, [data["frames"][i]["duration"] for i in indices],
                     tag.get("loop", tag.get("repeat", 0) == 0), historical, note)
        add_atlas(key, (path.parent / data["meta"]["image"]).relative_to(ROOT), frames)
        if key == "Front":
            front_data = data

    # The rear redraw has no new idle yet. Keep its source stand explicitly labelled.
    add_atlas("RearStand", "alisa/back_walk/source/Back_native.png",
              [dict(x=0, y=0, w=36, h=86, pivotX=18, pivotY=85)])
    add_clip("RearStand/idle", "Спина — исходная стойка (один кадр)", "01 Спина — новая основа",
             "RearStand", [0], [1000], True,
             note="Исходная неподвижная стойка. Отдельный новый idle со спины ещё не нарисован.")

    dance_tag = next(t for t in front_data["meta"]["frameTags"] if t["name"] == "dance_original")
    dance_durations = [front_data["frames"][i]["duration"]
                       for i in range(dance_tag["from"], dance_tag["to"] + 1)]
    for colour, label in [("green", "зелёные"), ("red", "красные")]:
        key = f"Dance{colour.title()}"
        frames = [dict(x=(i % 10) * 36, y=(i // 10) * 86, w=36, h=86, pivotX=15, pivotY=85)
                  for i in range(40)]
        add_atlas(key, f"recolor/{colour}_eyes/Altushka_{colour}_atlas.png", frames)
        add_clip(f"{key}/dance", f"Исходный танец — {label} глаза", "04 Варианты глаз",
                 key, list(range(5, 40)) + list(range(5)), dance_durations, True,
                 note="Сохранённый вариант исходного танца. Ходьба использует основной скин с голубыми глазами.")

    background = ROOT / "alisa/rear_key_redraw/Alisa_scene_background.png"
    copy_if_changed(background, DEST / "Environment/Alisa_scene_background.png")
    clips.sort(key=lambda clip: (clip["historical"], clip["group"]))
    result = dict(nativeWidth=36, nativeHeight=86, pixelsPerUnit=16,
                  defaultKey="RearRedraw/walk_back", atlases=atlases, clips=clips)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if not MANIFEST.exists() or MANIFEST.read_text("utf-8") != encoded:
        MANIFEST.write_text(encoded, encoding="utf-8", newline="\n")
    print(f"Unity sources: {len(atlases)} atlases, {len(clips)} clips, native 36x86; textures copied byte for byte.")


if __name__ == "__main__":
    main()
