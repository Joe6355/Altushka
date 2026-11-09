"""Export the in-place eight-direction preview with Blender's local FFmpeg DLLs."""
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'alisa/rear_key_redraw/source'))
from encode import encode
from refdecode import decode_reference

POSITIONS = {'n':(160,99),'ne':(237,113),'e':(272,171),'se':(233,224),
             's':(160,232),'sw':(87,224),'w':(48,171),'nw':(83,113)}
M = np.array([[65.481,128.553,24.966],[-37.797,-74.203,112.0],
              [112.0,-93.786,-18.214]], np.float32)/255


def main():
    data = json.loads((OUT/'Alisa_motion_polished.json').read_text('utf-8'))
    atlas = Image.open(OUT/data['meta']['image']).convert('RGBA')
    floor = Image.open(ROOT/'alisa/rear_key_redraw/Alisa_scene_background.png').convert('RGBA')
    tags = {tag['name']:tag for tag in data['meta']['frameTags']}
    cached = []
    for kind, count in (('walk',8),('idle',4)):
        for index in range(count):
            scene = floor.copy()
            for direction,(x,y) in POSITIONS.items():
                tag = tags[kind+'_'+direction]
                rect = data['frames'][tag['from']+index]['frame']
                cel = atlas.crop((rect['x'],rect['y'],rect['x']+36,rect['y']+86))
                scene.alpha_composite(cel,(x-tag['pivot']['x'],y-85))
            yuv = np.rint(np.asarray(scene.convert('RGB')).astype(np.float32)@M.T+[16,128,128]).astype(np.uint8)
            cached.append(tuple(yuv[:,:,i].repeat(4 if i==0 else 2,0).repeat(4 if i==0 else 2,1) for i in range(3)))
    indices = list(range(8))*6 + list(range(8,12))
    durations = [10]*48 + [90,40,10,100]
    path = OUT/'Alisa_motion_polished.mp4'
    encode((cached[i] for i in indices),path,1280,960,100,durations=durations)
    starts = np.cumsum([0]+durations[:-1])/100
    count = 0
    error = 0
    for number,(timestamp,actual) in enumerate(decode_reference(path,raw=True)):
        assert abs(timestamp-starts[number])<1e-6 and actual[0].shape==(960,1280)
        for expected,plane in zip(cached[indices[number]],actual):
            error=max(error,int(np.abs(expected.astype(np.int16)-plane.astype(np.int16)).max()))
        count += 1
    assert count==52 and error<=6, (count,error)
    print(f'Verified MP4: {count} packets, 7.2s, 1280x960, all timestamps; maximum YUV error {error}.',flush=True)


if __name__=='__main__':main()
