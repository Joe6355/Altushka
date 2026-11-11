"""Encode the native Aseprite previews and verify the MP4 clocks and pixels."""
from pathlib import Path
import json
import hashlib
import subprocess
import sys
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'alisa/rear_key_redraw/source'))
from encode import encode
from refdecode import decode_reference

M=np.array([[65.481,128.553,24.966],[-37.797,-74.203,112],
            [112,-93.786,-18.214]],np.float32)/255

def planes(gif,number):
    gif.seek(number%gif.n_frames)
    assert gif.info['duration']==60
    rgb=np.asarray(gif.convert('RGB'),np.float32)
    h,w=rgb.shape[:2]
    a=np.clip(np.rint(rgb@M.T+[16,128,128]),0,255).astype(np.uint8)
    return a[:,:,0],*(np.rint(a[:,:,i].reshape(h//2,2,w//2,2).mean((1,3))).astype(np.uint8) for i in (1,2))

def export(stem,repeat=1):
    gif=Image.open(OUT/(stem+'.gif'));count=gif.n_frames*repeat;w,h=gif.size
    target=OUT/(stem+'.mp4')
    encode((planes(gif,i) for i in range(count)),target,w,h,100,durations=[6]*count)
    maximum=0;n=0
    for n,(timestamp,actual) in enumerate(decode_reference(target,raw=True),1):
        assert abs(timestamp-(n-1)*.06)<1e-6
        if (n-1)%10==0:
            for expected,plane in zip(planes(gif,n-1),actual):
                maximum=max(maximum,int(np.abs(expected.astype(np.int16)-plane.astype(np.int16)).max()))
    assert n==count and maximum<=6,(n,count,maximum)
    print(target.name, f'{w}x{h}, {count} frames, {count*.06:.2f}s, YUV maximum error {maximum}',flush=True)

def validate():
    doc=json.loads((OUT/'Alisa_confident_walk.json').read_text('utf-8'))
    frames=doc['frames'];assert len(frames)==28
    assert [f['duration'] for f in frames]==[60]*20+[300]*8
    tags=doc['meta']['frameTags']
    assert [(t['name'],t['from'],t['to']) for t in tags]==[
        ('walk_sw_reference',0,19),('idle_sw_reference',20,27)]
    atlas=Image.open(OUT/'Alisa_confident_walk_atlas.png').convert('RGBA')
    master=np.asarray(Image.open(HERE/'Original_master.png').convert('RGBA'))
    head=master[:31];mask=head[:,:,3]>0
    poses=json.loads((HERE/'poses.json').read_text('utf-8'))['poses']
    def rnd(v):return int(np.floor(v+.5))
    for i,f in enumerate(frames):
        r=f['frame'];assert (r['w'],r['h'])==(36,86)
        cel=np.asarray(atlas.crop((r['x'],r['y'],r['x']+36,r['y']+86)))
        assert set(np.unique(cel[:,:,3])) <= {0,255}
        p=poses[i] if i<20 else dict(sway=0,bob=0)
        dx,dy=3+rnd(-p['sway']*.3),rnd(p['bob'])
        yy,xx=np.nonzero(mask)
        assert np.array_equal(cel[yy+dy,xx+dx],head[yy,xx]),('head',i)
    original='recolor/blue_eyes/Altushka_blue_atlas.png'
    assert hashlib.sha256((ROOT/original).read_bytes()).digest()==hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+original],cwd=ROOT)).digest()
    print('Native validation: 28 cels, 36x86, 20x60ms walk, 8x300ms idle; original head pixels exact in every cel; original dance atlas unchanged.',flush=True)

if __name__=='__main__':
    validate()
    export('Alisa_confident_walk_close',5)
    export('Alisa_confident_walk_game')
