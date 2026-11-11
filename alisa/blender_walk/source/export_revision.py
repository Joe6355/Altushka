"""Export the front-quarter model with the palette from the original sprite."""

from collections import Counter
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from export_sprites import OUTPUT, ROOT, PALETTE, assemble, pixel_cel, previews

REVISION = OUTPUT/"revision"
WORK = ROOT/".tools"/"alisa_blender_revision"
ASEPRITE = "C:/Program Files (x86)/Steam/steamapps/common/Aseprite/Aseprite.exe"


def reference_cel():
    atlas = Image.open(ROOT/"recolor/blue_eyes/Altushka_blue_atlas.png").convert("RGBA")
    return atlas.crop((324,0,360,86)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)


def comparison(source, updated):
    old = Image.open(OUTPUT/"Alisa_walk_atlas.png").convert("RGBA").crop((0,0,36,86))
    panels = (
        ("Исходник",source),
        ("Первая 3D-проба",old),
        ("Новая модель",updated),
    )
    width,height = 240,511
    board = Image.new("RGBA",(len(panels)*width,height),(85,84,98,255))
    draw = ImageDraw.Draw(board)
    font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",20)
    for i,(caption,cel) in enumerate(panels):
        if i:
            draw.line((i*width,22,i*width,height-16),fill=(115,114,125),width=1)
        draw.text((i*width+width/2,23),caption,font=font,fill=(250,248,253),anchor="mm")
        board.alpha_composite(cel.resize((180,430),Image.Resampling.NEAREST),
                              (i*width+(width-180)//2,55))
    board.convert("RGB").save(REVISION/"Alisa_comparison.png",optimize=True)


def source_palette(original):
    pixels = np.asarray(original)[:45]
    rgb = pixels[...,:3][pixels[...,3]>128]
    counter = Counter(tuple(int(v) for v in p) for p in rgb)
    top = [color for color,_ in counter.most_common(84)]
    blue = [(r,g,b) for r,g,b in counter if b-r>37 and g-r>12 and b>90]
    colors = list(dict.fromkeys(top+blue+[tuple(int(v) for v in row) for row in PALETTE]))
    return np.array(colors,dtype=np.float32)


def main():
    metadata = json.loads((WORK/"render.json").read_text(encoding="utf-8"))
    source = reference_cel()
    palette = source_palette(source)
    frames = [pixel_cel(WORK/f"cel_{i:02}.png",24,palette=palette,painted_outline=True)
              for i in range(len(metadata["frames"]))]
    assert len({frame.tobytes() for frame in frames}) == len(frames)
    assemble(ASEPRITE,frames,output=REVISION,render_directory=WORK)
    comparison(source,frames[0])
    pivot = metadata["pivotSquare"][0]-24,metadata["pivotSquare"][1]
    previews(frames,pivot,metadata["travel"],output=REVISION,character_palette=palette)
    print("Verified revised 36x86 cels and review media.",metadata["checks"],flush=True)


if __name__ == "__main__":
    main()
