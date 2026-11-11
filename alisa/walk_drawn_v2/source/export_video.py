"""Verify and encode Aseprite previews; pixel drawing stays in Aseprite."""
from pathlib import Path
import hashlib,json,subprocess,sys
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

def planes(gif,index):
    gif.seek(index%gif.n_frames)
    a=np.asarray(gif.convert('RGB'),np.float32)
    h,w=a.shape[:2]
    yuv=np.clip(np.rint(a@M.T+[16,128,128]),0,255).astype(np.uint8)
    return yuv[:,:,0],*(np.rint(yuv[:,:,i].reshape(h//2,2,w//2,2).mean((1,3))).astype(np.uint8) for i in (1,2))

def export(stem,repeat):
    gif=Image.open(OUT/(stem+'.gif'))
    durations=[]
    for i in range(gif.n_frames):gif.seek(i);durations.append(gif.info['duration']//10)
    durations*=repeat
    count=len(durations);w,h=gif.size
    target=OUT/(stem+'.mp4')
    encode((planes(gif,i) for i in range(count)),target,w,h,100,durations=durations)
    maximum=0;clock=0
    for n,(time,actual) in enumerate(decode_reference(target,raw=True)):
        assert abs(time-clock/100)<1e-6
        if n%8==0:
            maximum=max(maximum,*(int(np.abs(e.astype(np.int16)-a.astype(np.int16)).max()) for e,a in zip(planes(gif,n),actual)))
        clock+=durations[n]
    assert n+1==count and maximum<=6,(n,count,maximum)
    print(f'{target.name}: {count} frames, {clock/100:.2f}s, max YUV error {maximum}',flush=True)

def validate():
    doc=json.loads((OUT/'Alisa_walk_drawn.json').read_text('utf-8'))
    assert [(t['from'],t['to']) for t in doc['meta']['frameTags']]==[(0,7),(8,11),(12,19),(20,23)]
    assert [t['pivot']['x'] for t in doc['meta']['frameTags']]==[18]*4
    durations=[f['duration'] for f in doc['frames']]
    assert durations==([120]*8+[600]*4)*2
    atlas=Image.open(OUT/'Alisa_walk_drawn_atlas.png').convert('RGBA')
    head=np.asarray(Image.open(HERE/'Original_face_master.png').convert('RGBA'))[:31]
    yy,xx=np.nonzero(head[:,:,3]>0)
    cells=[]
    for i,f in enumerate(doc['frames']):
        r=f['frame'];assert (r['w'],r['h'])==(36,86)
        cel=np.asarray(atlas.crop((r['x'],r['y'],r['x']+36,r['y']+86)))
        assert set(np.unique(cel[:,:,3]))<={0,255}
        cells.append(cel)
        if i<12:
            dy=[1,1,0,0,1,1,0,0,0,0,0,0][i]
            assert np.array_equal(cel[yy+dy,xx],head[yy,xx]),('head',i)
    for right,left in enumerate([4,5,6,7,0,1,2,3,8,9,10,11],12):
        assert np.array_equal(cells[right],cells[left][:,::-1]),('mirror',right,left)
    p='recolor/blue_eyes/Altushka_blue_atlas.png'
    assert (ROOT/p).read_bytes()==subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)
    print('Native: 36x86, two diagonals; 8x120ms walk / 4x600ms idle each; mirrored pixels and pivots verified; original head exact; dance unchanged.',flush=True)

if __name__=='__main__':
    validate();export('Alisa_walk_drawn_close',6);export('Alisa_walk_drawn_game',1)
