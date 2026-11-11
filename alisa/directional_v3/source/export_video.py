"""Validate native deliverables and encode Aseprite's rendered previews."""
from pathlib import Path
from collections import deque
import hashlib,json,sys
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

def components(mask):
    seen=set();sizes=[]
    for y,x in zip(*np.where(mask)):
        if (y,x) in seen:continue
        q=deque([(y,x)]);seen.add((y,x));n=0
        while q:
            yy,xx=q.popleft();n+=1
            for oy in (-1,0,1):
                for ox in (-1,0,1):
                    k=yy+oy,xx+ox
                    if 0<=k[0]<86 and 0<=k[1]<36 and mask[k] and k not in seen:
                        seen.add(k);q.append(k)
        sizes.append(n)
    return sizes

def validate():
    doc=json.loads((OUT/'Alisa_directional_v3.json').read_text('utf-8'))
    tags=doc['meta']['frameTags'];assert len(tags)==12
    assert len(doc['frames'])==96
    atlas=Image.open(OUT/'Alisa_directional_v3_atlas.png').convert('RGBA')
    assert atlas.size==(432,688)
    cells=[]
    for item in doc['frames']:
        r=item['frame'];assert (r['w'],r['h'])==(36,86)
        a=np.array(atlas.crop((r['x'],r['y'],r['x']+36,r['y']+86)))
        assert set(np.unique(a[:,:,3]))<={0,255}
        assert len([n for n in components(a[:,:,3]>0) if n>5])==1,'Detached leg/body fragment'
        assert not a[:,[0,35],3].any(),'Clipped horizontal silhouette'
        foot_rows=np.where((a[:,:,3]>0).any(axis=1))[0]
        assert 81<=foot_rows[-1]<=85,'Foot outside the authored depth range'
        cells.append(a)
    order=['s','n','sw','se','nw','ne'];bob=[0,1,1,1,0,0,0,1,1,1,0,0,0,0,0,0]
    for row,d in enumerate(order):
        start=row*16;walk,idle=tags[row*2:row*2+2]
        assert (walk['name'],walk['from'],walk['to'])==('walk_'+d,start,start+11)
        assert (idle['name'],idle['from'],idle['to'])==('idle_'+d,start+12,start+15)
        assert [f['duration'] for f in doc['frames'][start:start+16]]==[80]*12+[600]*4
        feet=[int(np.where((c[:,:,3]>0).any(axis=1))[0][-1]) for c in cells[start:start+12]]
        assert max(abs(feet[(i+1)%12]-feet[i]) for i in range(12))<=2,('foot pop',d,feet)
        assert len({c.tobytes() for c in cells[start:start+12]})==12,('repeated walk pose',d)
        for tag in (walk,idle):assert tag['pivot']==dict(x=18,y=85) and tag['loop']
        if d in ('s','n','sw','nw'):
            head=np.array(Image.open(HERE/('Head_'+d+'.png')).convert('RGBA'))
            yy,xx=np.where(head[:,:,3]>0)
            for i in range(16):assert np.array_equal(cells[start+i][yy+bob[i],xx],head[yy,xx]),('head',d,i)
            old=np.array(Image.open(HERE/'history/initial_v3/Alisa_directional_v3_atlas.png').convert('RGBA'))
            previous=json.loads((HERE/'history/initial_v3/Alisa_directional_v3.json').read_text())
            old_tag=next(t for t in previous['meta']['frameTags'] if t['name']=='idle_'+d)
            r=previous['frames'][old_tag['from']]['frame']
            original=old[r['y']:r['y']+31,r['x']:r['x']+36]
            assert np.array_equal(head[:31],original),('appearance changed',d)
            skirt=np.array(Image.open(HERE/('Skirt_'+d+'.png')).convert('RGBA'))
            r,b=skirt[:,:,0].astype(int),skirt[:,:,2].astype(int)
            assert not ((r-b>15)&(skirt[:,:,3]>0)).any(),('skin carried by skirt',d)
        if d in ('n','nw','ne'):
            for cell in cells[start:start+16]:
                r,g,b=[cell[:32,:,k].astype(int) for k in range(3)]
                assert not ((b-r>40)&(g-r>40)&(cell[:32,:,3]>0)).any(),'Eye colour in rear hair'
    for left,right in ((32,48),(64,80)):
        for i in range(16):
            phase=(i+6)%12 if i<12 else i
            assert np.array_equal(cells[right+i],cells[left+phase][:,::-1]),('mirror',right,i)
    hashes=json.loads((HERE/'approved_hashes.json').read_text())
    for p,expected in hashes.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==expected,('approved file changed',p)
    report=dict(native=[36,86],cels=96,tags=12,walkMs=960,idleMs=2400,walkFrames=12,maxTorsoBob=1,
                stableHeads=True,headAppearanceUnchanged=True,cleanGarmentMasks=True,
                noLegHeightNormalisation=True,maxFootExtentStep=2,binaryAlpha=True,connectedBodies=True,mirrors=True,
                approvedFilesUnchanged=len(hashes))
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n','utf-8')
    print('Native OK: 36x86; 96 cels, 12 tags; original v3 heads unchanged; connected silhouettes; mirrored phases; approved A/D and dance unchanged.',flush=True)

def planes(gif,index):
    gif.seek(index%gif.n_frames)
    a=np.asarray(gif.convert('RGB'),np.float32);h,w=a.shape[:2]
    yuv=np.clip(np.rint(a@M.T+[16,128,128]),0,255).astype(np.uint8)
    return yuv[:,:,0],*(np.rint(yuv[:,:,i].reshape(h//2,2,w//2,2).mean((1,3))).astype(np.uint8) for i in (1,2))

def export(stem):
    gif=Image.open(OUT/(stem+'.gif'));durations=[]
    for i in range(gif.n_frames):gif.seek(i);durations.append(gif.info['duration']//10)
    target=OUT/(stem+'.mp4');w,h=gif.size
    encode((planes(gif,i) for i in range(len(durations))),target,w,h,100,durations=durations)
    clock=0;maximum=0;n=-1
    for n,(time,actual) in enumerate(decode_reference(target,raw=True)):
        assert abs(time-clock/100)<1e-6
        if n%12==0:maximum=max(maximum,*(int(np.abs(a.astype(np.int16)-e.astype(np.int16)).max()) for a,e in zip(actual,planes(gif,n))))
        clock+=durations[n]
    assert n+1==len(durations) and maximum<=6,(n,len(durations),maximum)
    print(f'{target.name}: {len(durations)} frames; {clock/100:.2f}s; decoded timing OK, max sampled YUV error {maximum}',flush=True)

if __name__=='__main__':
    validate()
    for stem in ('Alisa_directional_v3_smooth','Alisa_directional_v3_game_smooth'):export(stem)
