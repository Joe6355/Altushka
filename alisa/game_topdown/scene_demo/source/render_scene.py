
from pathlib import Path
from dataclasses import dataclass
from struct import unpack_from
import bisect,json,math
import numpy as np
from PIL import Image,ImageDraw
from morph import pixel_morph
from encode import encode
from refdecode import decode_reference

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent
GAME=ROOT.parents[1]
PROJECT=ROOT.parents[3]
STAGE=(320,240);ZOOM=4;TICK=20
BACKGROUND=Image.open(OUT/'Alisa_scene_background.png').convert('RGBA')
atlas=Image.open(GAME/'Alisa_game_atlas.png').convert('RGBA')
meta=json.loads((GAME/'Alisa_game_atlas.json').read_text('utf-8'))
ANIMS={}
for tag in meta['meta']['frameTags']:
    images=[];durations=[]
    for i in range(tag['from'],tag['to']+1):
        f=meta['frames'][i];v=f['frame'];x,y,w,h=[v[k] for k in ('x','y','w','h')]
        images.append(atlas.crop((x,y,x+w,y+h)));durations.append(f['duration'])
    ANIMS[tag['name']]=(images,durations,np.r_[0,np.cumsum(durations)].tolist())
dance_atlas=Image.open(PROJECT/'recolor/blue_eyes/Altushka_blue_atlas.png').convert('RGBA')
DANCE=[dance_atlas.crop((i%10*36,i//10*86,i%10*36+36,i//10*86+86)) for i in range(40)]
entry_atlas=Image.open(OUT/'Alisa_dance_entry_atlas.png').convert('RGBA')
BRIDGE=[entry_atlas.crop((n*36,0,(n+1)*36,86)) for n in range(8)]
assert BRIDGE[0].tobytes()==ANIMS['idle_down'][0][0].tobytes()
assert BRIDGE[-1].tobytes()==DANCE[0].tobytes()

def anim(name,t,offset=0):
    images,durations,starts=ANIMS[name]
    ms=(t+offset)%starts[-1]
    return images[bisect.bisect_right(starts,ms)-1]

def ease(u):
    u=max(0.,min(1.,u));return u*u*(3-2*u)

def travel_fraction(ms,duration):
    # Short acceleration and braking; a constant speed over the main step.
    t=max(0.,min(float(ms),float(duration)));e=240.
    if t<e:d=.5*t*t/e
    elif t<duration-e:d=t-e/2
    else:d=duration-e-.5*(duration-t)**2/e
    return d/(duration-e)

@dataclass
class Node:
    label:str
    kind:str
    duration:int
    start:int
    p0:tuple
    p1:tuple
    a:object=None
    b:object=None
    name:str=''
    offset:int=0

    def state(self,local):
        t=max(0,min(local,self.duration))
        if self.kind=='idle':
            pose=anim(self.name,t)
        elif self.kind=='walk':
            pose=anim(self.name,t,self.offset)
        elif self.kind=='morph':
            pose=pixel_morph(self.a,self.b,ease(t/self.duration))
        elif self.kind in ('entry','exit'):
            u=ease(t/self.duration) if self.kind=='entry' else 1-ease(t/self.duration)
            value=u*7;i=min(6,int(value));f=value-i
            pose=pixel_morph(BRIDGE[i],BRIDGE[i+1],f)
        elif self.kind=='dance':
            pose=DANCE[int(t//100)%40]
        else:raise ValueError(self.kind)
        q=travel_fraction(t,self.duration) if self.kind=='walk' else 0
        p=(self.p0[0]+(self.p1[0]-self.p0[0])*q,self.p0[1]+(self.p1[1]-self.p0[1])*q)
        return pose,p

NODES=[]
position=(96.,194.);current=ANIMS['idle_down'][0][0];clock=0
def add(label,kind,duration,**kw):
    global current,position,clock
    assert duration%TICK==0
    node=Node(label,kind,duration,clock,position,kw.pop('p1',position),**kw)
    first,p=node.state(0)
    assert first.tobytes()==current.tobytes(),('Pose discontinuity',label)
    assert p==position
    current,position=node.state(duration)
    NODES.append(node);clock+=duration
    return node
def idle(view,ms):
    return add('Ожидание: '+view,'idle',ms,name='idle_'+view)
def change(view):
    add('Поворот: '+view,'morph',160,a=current,b=ANIMS['idle_'+view][0][0])
def route(view,to,ms):
    change(view)
    add('Начало шага: '+view,'morph',160,a=current,b=ANIMS['walk_'+view][0][2])
    add('Ходьба: '+view,'walk',ms,name='walk_'+view,offset=240,p1=tuple(map(float,to)))
    add('Остановка: '+view,'morph',160,a=current,b=ANIMS['idle_'+view][0][0])
    idle(view,320)

idle('down',1440)
route('right',(224,194),2880)
route('up',(224,132),2880)
route('left',(96,132),2880)
route('down',(96,194),2880)
route('right',(160,194),1920)
change('down');idle('down',480)
ENTRY=add('Подготовка к танцу','entry',800)
DANCENODE=add('Исходный танец, два повтора','dance',8000)
EXIT=add('Возвращение из танца','exit',800)
idle('down',2880)
TOTAL=clock
assert TOTAL==32000,TOTAL
assert {n.name for n in NODES if n.kind=='walk'}=={'walk_down','walk_up','walk_left','walk_right'}
STARTS=[n.start for n in NODES]
def scene_state(t):
    i=min(len(NODES)-1,bisect.bisect_right(STARTS,t)-1)
    node=NODES[i]
    pose,p=node.state(t-node.start)
    return pose,p,node

def render(t):
    pose,p,node=scene_state(t)
    px,py=[int(round(v)) for v in p]
    x,y=px-18,py-85
    a=np.asarray(pose);box=pose.getbbox()
    assert box and a[:,:,3].max()==255
    assert x+box[0]>=0 and y+box[1]>=0 and x+box[2]<=STAGE[0] and y+box[3]<=STAGE[1],(t,node.label,box,p)
    out=BACKGROUND.copy()
    # A low, softly shaded pixel-art contact shadow follows the stance width.
    ys,xs=np.where(a[72:,:,3]>0)
    radius=max(7,min(18,int((xs.max()-xs.min())*.52+2))) if len(xs) else 9
    shadow=Image.new('RGBA',STAGE)
    d=ImageDraw.Draw(shadow);d.ellipse((px-radius,py-2,px+radius,py+2),fill=(16,19,29,60))
    out.alpha_composite(shadow);out.alpha_composite(pose,(x,y))
    return out.convert('RGB')

MATRIX=np.array([[65.481,128.553,24.966],[-37.797,-74.203,112.0],[112.0,-93.786,-18.214]],np.float32)/255
def yuv(im):
    rgb=np.asarray(im).astype(np.float32)
    values=np.rint(rgb@MATRIX.T+[16,128,128]).astype(np.uint8)
    return (values[:,:,0].repeat(ZOOM,0).repeat(ZOOM,1),
            values[:,:,1].repeat(ZOOM//2,0).repeat(ZOOM//2,1),
            values[:,:,2].repeat(ZOOM//2,0).repeat(ZOOM//2,1))
def planes():
    for n,t in enumerate(range(0,TOTAL,TICK)):
        yield yuv(render(t))

def save_review():
    values=[0,3000,7000,11000,14500,ENTRY.start+380,DANCENODE.start+1000,EXIT.start+400,TOTAL-500]
    sheet=Image.new('RGB',(960,3*260),(42,44,53))
    draw=ImageDraw.Draw(sheet)
    for n,t in enumerate(values):
        image=render(t);x,y=n%3*320,n//3*260
        sheet.paste(image,(x,y))
        draw.text((x+5,y+243),f'{t/1000:.2f}s {scene_state(t)[2].kind}',fill=(235,235,240))
    sheet.save(ROOT/'scene_contact.png')
    render(DANCENODE.start+700).resize((1280,960),Image.Resampling.NEAREST).save(OUT/'Alisa_scene_poster.png')
    data={'durationMs':TOTAL,'fps':50,'videoSize':{'w':1280,'h':960},'nativeSceneSize':{'w':320,'h':240},
          'spriteSize':{'w':36,'h':86},'danceSource':'recolor/blue_eyes/Altushka_blue_atlas.png',
          'danceRepeats':2,'clips':[{'label':n.label,'kind':n.kind,'startMs':n.start,'durationMs':n.duration,
                                    'from':list(n.p0),'to':list(n.p1)} for n in NODES]}
    (OUT/'Alisa_scene_timeline.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    for n in NODES:print(f'{n.start/1000:5.2f} - {(n.start+n.duration)/1000:5.2f} {n.label}',flush=True)

def validate_source_and_motion():
    # The dance segment is exactly the original 40-frame sequence twice,
    # with no new body deformation, timing or colour substitutions.
    for k in range(400):
        t=DANCENODE.start+k*TICK
        pose,p,node=scene_state(t)
        assert pose.tobytes()==DANCE[(k//5)%40].tobytes()
    for node in NODES:
        for t in (0,node.duration//2,node.duration):
            pose,p=node.state(t)
            assert pose.size==(36,86)
            assert set(np.unique(np.asarray(pose)[:,:,3]))<={0,255}
    # Include actual start/end poses at every state boundary.
    for a,b in zip(NODES,NODES[1:]):
        pa,xa=a.state(a.duration);pb,xb=b.state(0)
        assert pa.tobytes()==pb.tobytes() and xa==xb
    assert all(abs(travel_fraction(t,n.duration)-q)<1e-9 for n in NODES if n.kind=='walk' for t,q in ((0,0),(n.duration,1)))
    print('Verified source dance, all four walk directions, exact state joins, 36x86 sprite scale, 32-second timeline.',flush=True)

def verify_video(path):
    high=0;count=0
    for i,(ts,decoded) in enumerate(decode_reference(path,raw=True)):
        assert abs(ts-i*.02)<1e-6,(i,ts)
        assert decoded[0].shape==(960,1280)
        if i%5==0 or any(abs(i*TICK-n.start)<=40 for n in NODES):
            expected=yuv(render(i*TICK))
            for a,b in zip(expected,decoded,strict=True):
                high=max(high,int(np.abs(a.astype(np.int16)-b.astype(np.int16)).max()))
        count+=1
    assert count==TOTAL//TICK
    assert high<=6,high
    print('Decoded verification:',count,'frames,',TOTAL/1000,'seconds; max sampled YUV error',high,flush=True)

if __name__=='__main__':
    save_review();validate_source_and_motion()
    import sys
    if '--render' in sys.argv:
        path=OUT/'Alisa_full_scene.mp4'
        encode(planes(),path,1280,960,100,[2]*(TOTAL//TICK))
        verify_video(path)
        print('Saved',path,path.stat().st_size,flush=True)
