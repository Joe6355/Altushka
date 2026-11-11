"""Pack mirrored game walks, phase-aligned at the sole, and the corresponding idles."""

import json

from PIL import Image

from export_revision import ASEPRITE, reference_cel, source_palette
from export_sprites import OUTPUT, ROOT, WIDTH, HEIGHT, export_aseprite, pixel_cel, preview_pose, previews


OUT = OUTPUT / "game"
WORK = ROOT / ".tools" / "alisa_blender_game"
STEM = "Alisa_diagonals"


def frame_at(background,time,scale,walk,idle,pivot,playback,stride):
    start = .32
    half = 1.36
    move_time = max(0.0,min(time-start,2*half))
    left = move_time >= half
    speed = stride*playback
    x = 149+speed*(min(move_time,half)-max(0.0,move_time-half))
    y = 105+speed*move_time
    if time<start or time>=start+2*half:
        rest_time = time if time<start else time-start-2*half
        sprite = idle[left][int(max(0,rest_time)*5)%len(idle[left])]
    else:
        sprite = walk[left][int(move_time*playback*len(walk[left]))%len(walk[left])]
    return preview_pose(background,sprite,x,y,pivot[left],scale)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    data = json.loads((WORK/"render.json").read_text(encoding="utf-8"))
    palette = source_palette(reference_cel())
    walk_se = [pixel_cel(WORK/f"walk_{i:02}.png",24,palette=palette,painted_outline=True)
               for i in range(data["walkCels"])]
    idle_se = [pixel_cel(WORK/f"idle_{i:02}.png",24,palette=palette,painted_outline=True)
               for i in range(data["idleCels"])]
    walk_sw = [walk_se[(i+len(walk_se)//2)%len(walk_se)].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
               for i in range(len(walk_se))]
    idle_sw = [cel.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for cel in idle_se]
    assert len({cel.tobytes() for cel in idle_se})>1
    assert all(cel.tobytes()!=walk_se[0].tobytes() for cel in idle_se)
    x,y = map(round,data["pivot"])
    pivots = ((x,y),(WIDTH-x,y))
    clips = (
        ("walk_se",len(walk_se),50),
        ("walk_sw",len(walk_sw),50),
        ("idle_se",len(idle_se),200),
        ("idle_sw",len(idle_sw),200),
    )
    frames = walk_se+walk_sw+idle_se+idle_sw
    document,size = export_aseprite(ASEPRITE,frames,output=OUT,render_directory=WORK,name=STEM,
                                  clips=clips,columns=len(walk_se))
    assert size == (WIDTH*len(walk_se),HEIGHT*3),size
    first = 0
    for tag,(name,count,delay) in zip(document["meta"]["frameTags"],clips,strict=True):
        assert (tag["name"],tag["from"],tag["to"]) == (name,first,first+count-1)
        assert all(cel["duration"]==delay for cel in document["frames"][first:first+count])
        px,py = pivots[name.endswith("_sw")]
        tag["pivot"] = {"x":px,"y":py}
        tag["label"] = ("Ходьба" if name.startswith("walk") else "Стойка")+" вниз-"+(
            "влево" if name.endswith("_sw") else "вправо")
        first += count
    document["meta"]["gameplay"] = {"playbackRate":data["playback"],"stridePx":data["travel"]}
    (OUT/f"{STEM}.json").write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assert len({cel.tobytes() for cel in walk_se})==len(walk_se)
    assert data["stanceErrorPixels"]<.08

    def draw_frame(background,time,scale):
        return frame_at(background,time,scale,(walk_se,walk_sw),(idle_se,idle_sw),pivots,
                        data["playback"],data["travel"])

    previews(walk_se,pivots[0],None,output=OUT,character_palette=palette,draw_frame=draw_frame)
    print("20 walk and 6 idle cels per direction, 36x86, mirrored at half a cycle:",data,flush=True)


if __name__ == "__main__":
    main()
