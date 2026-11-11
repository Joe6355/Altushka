"""Verify the native step and encode Aseprite previews without drawing pixels."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'alisa/directional_v3/source'))
from export_video import components,planes
sys.path.insert(0,str(ROOT/'alisa/rear_key_redraw/source'))
from encode import encode
from refdecode import decode_reference

def cells(folder,stem):
    doc=json.loads((folder/(stem+'.json')).read_text('utf-8'))
    image=Image.open(folder/doc['meta']['image']).convert('RGBA')
    result=[]
    for f in doc['frames']:
        r=f['frame'];assert (r['w'],r['h'])==(36,86)
        result.append(np.array(image.crop((r['x'],r['y'],r['x']+36,r['y']+86))))
    return doc,result

def validate():
    doc,c=cells(OUT,'Alisa_step_contact')
    assert len(c)==32
    expected=[('walk_sw',0,11),('idle_sw',12,15),('walk_se',16,27),('idle_se',28,31)]
    assert [(t['name'],t['from'],t['to']) for t in doc['meta']['frameTags']]==expected
    assert [f['duration'] for f in doc['frames']]==([80]*12+[600]*4)*2
    for t in doc['meta']['frameTags']:assert t['pivot']==dict(x=18,y=85) and t['loop']
    for i,a in enumerate(c):
        assert set(np.unique(a[:,:,3]))<={0,255}
        assert len([v for v in components(a[:,:,3]>0) if v>5])==1,('disconnected',i)
        assert not a[:,[0,35],3].any(),('clipped',i)
    head=np.array(Image.open(HERE/'Head_sw.png').convert('RGBA'));yy,xx=np.where(head[:,:,3]>0)
    bob=[0,1,1,0,0,0,0,1,1,0,0,0]+[0]*4
    for i in range(16):assert np.array_equal(c[i][yy+bob[i],xx],head[yy,xx]),('head changed',i)
    for i in range(16):assert np.array_equal(c[16+i],c[(i+6)%12 if i<12 else i][:,::-1]),('mirror',i)
    old,previous=cells(ROOT/'alisa/directional_v3','Alisa_directional_v3')
    for i in range(4):
        assert np.array_equal(c[12+i],previous[44+i]),('idle changed',i)
        assert np.array_equal(c[28+i],previous[60+i]),('right idle changed',i)
    trace=json.loads((HERE/'stance_trace.json').read_text())
    for t in trace:
        assert (t['worldX'],t['worldY'])==(10,85)
        assert c[t['frame']][t['toeY'],t['toeX'],3]==255
    for i,knee,ankle in [(6,(20,65),(25,70)),(7,(18,66),(23,73)),(8,(16,67),(19,76))]:
        assert knee[0]<ankle[0]
        assert c[i][knee[1],knee[0],3]>0 and c[i][ankle[1],ankle[0],3]>0
    for p,h in json.loads((HERE/'approved_hashes.json').read_text()).items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    report=dict(native=[36,86],frames=32,tags=4,walkFrames=12,walkMs=960,
                headUnchanged=True,idleUnchanged=True,mirrorPhase=6,
                plantedToeSamples=len(trace),toeWorldPoint=[10,85],approvedHashesUnchanged=7)
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n','utf-8')
    print('Native OK: 36x86; unchanged face/idles; 12-phase mirrored walk; 5 planted-toe samples; knee leads ankle; 7 approved hashes unchanged.',flush=True)

def export(stem):
    gif=Image.open(OUT/(stem+'.gif'));durations=[]
    for i in range(gif.n_frames):gif.seek(i);durations.append(gif.info['duration']//10)
    target=OUT/(stem+'.mp4');w,h=gif.size
    encode((planes(gif,i) for i in range(len(durations))),target,w,h,100,durations=durations)
    clock=0;maximum=0;n=-1
    for n,(time,actual) in enumerate(decode_reference(target,raw=True)):
        assert abs(time-clock/100)<1e-6
        if n%12==0:maximum=max(maximum,*(int(np.abs(a.astype(np.int16)-b.astype(np.int16)).max()) for a,b in zip(actual,planes(gif,n))))
        clock+=durations[n]
    assert n+1==len(durations) and maximum<=6,(n,len(durations),maximum)
    print(f'{target.name}: {len(durations)} frames, {clock/100:.2f}s, max sampled YUV error {maximum}',flush=True)

if __name__=='__main__':
    validate()
    for stem in ('Alisa_step_contact_close','Alisa_step_contact_game'):export(stem)
