"""Bake the transparent Blender render into native sprites and review media."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

SOURCE = Path(__file__).resolve().parent
OUTPUT = SOURCE.parent
ROOT = OUTPUT.parents[1]
RENDER = ROOT / ".tools" / "alisa_blender"
WIDTH, HEIGHT = 36, 86
NATIVE_PALETTE = """
14141c 22222b 30303a 42414c
848494 a5a6b6 c5c7d4 e0e2eb f1f2f7 fffdfc
af6276 c78194 eea2ab fac3b9 ffdfd5 fff0e7
19354e 286894 279cc3 37bad8 67d9e8 b4eff2
""".split()
PALETTE = np.array([list(bytes.fromhex(hex_color)) for hex_color in NATIVE_PALETTE], dtype=np.float32)
INK = (13, 12, 19)
YUV = np.array([[65.481,128.553,24.966],[-37.797,-74.203,112],
                [112,-93.786,-18.214]],np.float32)/255


def nearest_colors(rgb, palette):
    error = (rgb[...,None,:]-palette)**2
    # Saturated accents must not be mistaken for gray at this scale.
    error *= (1.0,1.12,1.0)
    return error.sum(axis=-1).argmin(axis=-1)


def pixel_cel(path, left, *, palette=PALETTE, painted_outline=False):
    raster = np.array(Image.open(path).convert("RGBA"),dtype=np.float32)
    ss = raster.shape[0]//HEIGHT
    assert raster.shape == (HEIGHT*ss,HEIGHT*ss,4)
    samples = raster.reshape(HEIGHT,ss,HEIGHT,ss,4).transpose(0,2,1,3,4)
    alpha = samples[...,3]/255
    sample_weight = np.linspace(.76,1.0,(ss+1)//2)
    sample_weight = np.concatenate((sample_weight,sample_weight[:ss//2][::-1]))
    weights = alpha*sample_weight[:,None]*sample_weight[None,:]
    coverage = weights.sum(axis=(2,3))
    solid = coverage >= .43*sample_weight.sum()**2
    solid_weights = weights[solid]
    solid_samples = samples[solid]
    colors = nearest_colors(solid_samples[...,:3],palette)
    # Choose a rendered shade by area coverage to preserve hard color clusters.
    votes = (np.eye(len(palette),dtype=np.float32)[colors]*solid_weights[...,None]).sum(axis=(1,2))
    result = np.zeros((HEIGHT,HEIGHT,3),dtype=np.uint8)
    result[solid] = palette[votes.argmax(axis=-1)]

    # Keep the cyan eye readable when the iris straddles the pixel grid.
    if not painted_outline:
        r,g,b = np.moveaxis(samples[...,:3],-1,0)
        eye = (b-r>38)&(g-r>15)&(b>110)
        eye_weights = weights*eye
        eye_coverage = eye_weights.sum(axis=(2,3))
        eye_pixel = (eye_coverage > .24*sample_weight.sum()**2)&solid
        accent = (samples[...,:3]*eye_weights[...,None]).sum(axis=(2,3))
        eye_colors = PALETTE[-5:]
        result[eye_pixel] = eye_colors[nearest_colors(accent[eye_pixel]/eye_coverage[eye_pixel,None],eye_colors)]

    padded = np.pad(solid,1)
    outline = (padded[:-2,1:-1]|padded[2:,1:-1]|padded[1:-1,:-2]|padded[1:-1,2:]) & ~solid
    if painted_outline:
        dark = solid & (result.max(axis=-1)<17)
        rim = np.pad(dark,1)
        outline &= ~(rim[:-2,1:-1]|rim[2:,1:-1]|rim[1:-1,:-2]|rim[1:-1,2:])
    result[outline] = INK
    result[~(solid|outline)] = 0
    visibility = solid|outline
    y,x = np.nonzero(visibility)
    assert x.min()>=left and x.max()<left+WIDTH, (path.name,x.min(),x.max(),left)
    if painted_outline:
        assert raster[[0,-1],:,3].max()<128, (path.name,y.min(),y.max())
    else:
        assert y.min()>0 and y.max()<HEIGHT-1, (path.name,y.min(),y.max())
    pixels = np.dstack((result,np.where(visibility,255,0).astype(np.uint8)))
    return Image.fromarray(pixels[:,left:left+WIDTH])


def export_aseprite(aseprite, frames, *, output, render_directory, name, clips=(), columns=None):
    for i,cel in enumerate(frames):
        cel.save(render_directory/f"pixel_{i:02}.png")
    command = [
        aseprite,"--batch",
        "--script-param",f"out={output.as_posix()}",
        "--script-param",f"render={render_directory.as_posix()}",
        "--script-param",f"frames={len(frames)}",
        "--script-param",f"name={name}",
    ]
    if clips:
        spec = ",".join(f"{label}:{count}:{delay}" for label,count,delay in clips)
        command.extend(("--script-param",f"clips={spec}"))
    if columns is not None:
        command.extend(("--script-param",f"columns={columns}"))
    subprocess.run(command+["--script",str(SOURCE/"assemble.lua")],check=True)
    sheet = Image.open(output/f"{name}_atlas.png").convert("RGBA")
    document = json.loads((output/f"{name}.json").read_text(encoding="utf-8"))
    assert len(document["frames"]) == len(frames)
    for actual,expected in zip(document["frames"],frames):
        rect = actual["frame"]
        x,y,w,h = (rect[key] for key in ("x","y","w","h"))
        assert (w,h) == (WIDTH,HEIGHT)
        assert sheet.crop((x,y,x+w,y+h)).tobytes() == expected.tobytes()
    return document,sheet.size


def assemble(aseprite, frames, *, output=OUTPUT, render_directory=RENDER):
    document,size = export_aseprite(aseprite,frames,output=output,render_directory=render_directory,name="Alisa_walk")
    tag, = document["meta"]["frameTags"]
    assert (tag["name"],tag["from"],tag["to"]) == ("walk_se",0,len(frames)-1)
    assert size == (WIDTH*len(frames),HEIGHT),size
    assert sum(cel["duration"] for cel in document["frames"]) == 1000


def model_sheet(pixel):
    panel_width, height = 260, 520
    canvas = Image.new("RGBA",(panel_width*4,height),(76,77,91))
    draw = ImageDraw.Draw(canvas)
    for i in range(1,4):
        draw.line((i*panel_width,34,i*panel_width,height-34),fill=(99,100,114),width=1)
    for i,name in enumerate(("front","quarter","rear")):
        model = Image.open(RENDER/f"model_{name}.png").convert("RGBA")
        model = model.resize((488,488),Image.Resampling.LANCZOS)
        x = i*panel_width+(panel_width-model.width)//2
        canvas.alpha_composite(model,(x,14))
    sprite = pixel.resize((WIDTH*5,HEIGHT*5),Image.Resampling.NEAREST)
    canvas.alpha_composite(sprite,(3*panel_width+(panel_width-sprite.width)//2,56))
    canvas.convert("RGB").save(OUTPUT/"Alisa_model.png",optimize=True)


def preview_frame(bg,frames,time,pivot,travel,scale):
    sprite = frames[int((time%1)*len(frames)+1e-6)%len(frames)]
    x = 100+travel[0]*time
    y = 128+travel[1]*time
    return preview_pose(bg,sprite,x,y,pivot,scale)


def preview_pose(bg,sprite,x,y,pivot,scale):
    image = bg.copy()
    shadow = Image.new("RGBA",image.size)
    draw = ImageDraw.Draw(shadow)
    draw.ellipse((round(x-11),round(y-3),round(x+12),round(y+3)),fill=(24,23,30,57))
    draw.ellipse((round(x-8),round(y-2),round(x+9),round(y+2)),fill=(24,23,30,71))
    image.alpha_composite(shadow)
    image.alpha_composite(sprite,(round(x-pivot[0]),round(y-pivot[1])))
    return image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST).convert("RGB")


def previews(frames,pivot,travel,*,output=OUTPUT,character_palette=PALETTE,draw_frame=None):
    bg = Image.open(ROOT/"alisa/walk_redo/Alisa_scene_background.png").convert("RGBA")
    background_colors = 256-len(character_palette)-1
    floor_palette = bg.convert("RGB").quantize(colors=background_colors).getpalette()
    palette = Image.new("P",(1,1))
    palette.putpalette(floor_palette[:3*background_colors]+character_palette.astype(int).ravel().tolist()+list(INK))
    if draw_frame is None:
        def draw_frame(background,time,scale):
            return preview_frame(background,frames,time,pivot,travel,scale)
    gif = [
        draw_frame(bg,i/25,2).quantize(palette=palette,dither=Image.Dither.NONE)
        for i in range(100)
    ]
    gif[0].save(output/"Alisa_walk.gif",save_all=True,append_images=gif[1:],duration=40,loop=0,optimize=False)

    # Reuse the video encoder and decoder already used for the original walk study.
    sys.path.insert(0,str(ROOT/"alisa/walk_redo/source"))
    from encode import encode
    from refdecode import decode_reference

    def video_frame(index):
        image = np.asarray(draw_frame(bg,index/50,3),dtype=np.float32)
        h,w = image.shape[:2]
        yuv = np.clip(np.rint(image@YUV.T+[16,128,128]),0,255).astype(np.uint8)
        chroma = [np.rint(yuv[:,:,i].reshape(h//2,2,w//2,2).mean((1,3))).astype(np.uint8) for i in (1,2)]
        return yuv[:,:,0],*chroma

    target = output/"Alisa_walk.mp4"
    length = 200
    encode((video_frame(i) for i in range(length)),target,bg.width*3,bg.height*3,50)
    decoded = 0
    for time,planes in decode_reference(target,raw=True):
        assert abs(time-decoded/50)<1e-6,time
        assert planes[0].shape == (bg.height*3,bg.width*3)
        if decoded % 50 == 0:
            assert all(np.abs(a.astype(np.int16)-b.astype(np.int16)).max() <= 6
                       for a,b in zip(planes,video_frame(decoded)))
        decoded += 1
    assert decoded == length


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aseprite",default=shutil.which("aseprite") or
                        "C:/Program Files (x86)/Steam/steamapps/common/Aseprite/Aseprite.exe")
    parser.add_argument("--skip-video",action="store_true")
    args = parser.parse_args()
    data = json.loads((RENDER/"render.json").read_text(encoding="utf-8"))
    count = len(data["frames"])
    left = (HEIGHT-WIDTH)//2-1
    pivot = (data["pivotSquare"][0]-left,data["pivotSquare"][1])
    frames = [pixel_cel(RENDER/f"cel_{i:02}.png",left) for i in range(count)]
    assert len({frame.tobytes() for frame in frames}) == count
    assemble(args.aseprite,frames)
    model_sheet(frames[2])
    if not args.skip_video:
        previews(frames,pivot,data["travel"])
    report = dict(data["checks"],pivot=pivot,travelPerLoop=data["travel"],nativeSize=[WIDTH,HEIGHT],
                  count=count,loopMs=1000)
    (RENDER/"sprite_check.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Checked the atlas against every native cel.",report,flush=True)


if __name__ == "__main__":
    main()
