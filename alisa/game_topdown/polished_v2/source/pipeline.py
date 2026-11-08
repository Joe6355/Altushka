
from pathlib import Path
from functools import lru_cache
from struct import pack,pack_into,unpack_from
import json,zlib,math,bisect
import numpy as np
from PIL import Image,ImageDraw
import core,limbs
from encode import encode
from refdecode import decode_reference
R=Path(__file__).resolve().parent
OUT=R.parent;OUT.mkdir(exist_ok=True)
BG=Image.open(OUT/'Alisa_scene_background.png').convert('RGBA')
STEP=20;ZOOM=4
STRIDE=30.6666666667;CAM=3/9.2
V=core.VIEWS

def clip(name,view,count,ms,kind):
 result=[]
 for n in range(count):
  t=n*ms/1000
  ph=n/count*math.tau if kind=='walk' else t*math.tau
  result.append(core.character(view,ph,1 if kind=='walk' else 0,1 if kind=='dance' else 0,t))
 return (name,result,[ms]*count)

CLIPS=[clip('idle_'+v,v,8,360,'idle') for v in V]+[clip('walk_'+v,v,16,60,'walk') for v in V]+[clip('dance','down_left',40,100,'dance')]

def chunk(kind,data):return pack('<IH',len(data)+6,kind)+data
def export():
 total=sum(len(fr) for _,fr,_ in CLIPS);cols=16;rows=math.ceil(total/cols)
 sheet=Image.new('RGBA',(36*cols,86*rows));entries=[];tags=[];frames=[];i=0
 for name,fr,ds in CLIPS:
  tags.append({'name':name,'from':i,'to':i+len(fr)-1,'direction':'forward'})
  for im,ms in zip(fr,ds):
   x=i%cols*36;y=i//cols*86;sheet.paste(im,(x,y))
   entries.append({'filename':f'{name}_{i:03}.png','frame':{'x':x,'y':y,'w':36,'h':86},'rotated':False,'trimmed':False,'spriteSourceSize':{'x':0,'y':0,'w':36,'h':86},'sourceSize':{'w':36,'h':86},'duration':ms})
   frames.append((im,ms));i+=1
 sheet.save(OUT/'Alisa_polished_atlas.png',optimize=True)
 meta={'image':'Alisa_polished_atlas.png','format':'RGBA8888','size':{'w':sheet.width,'h':sheet.height},'scale':'1','frameTags':tags,'pivot':{'x':18,'y':85},'directions':list(V)}
 (OUT/'Alisa_polished_atlas.json').write_text(json.dumps({'frames':entries,'meta':meta},ensure_ascii=False,indent=2),encoding='utf-8')
 tagdata=pack('<H8x',len(tags))
 for t in tags:
  s=t['name'].encode();tagdata+=pack('<HHBH6x3BBH',t['from'],t['to'],0,0,112,188,220,0,len(s))+s
 payload=[]
 for n,(im,ms) in enumerate(frames):
  cs=[]
  if n==0:
   name='Алиса'.encode('utf-8');cs.append(chunk(0x2004,pack('<6HB3xH',3,0,0,0,0,0,255,len(name))+name));cs.append(chunk(0x2018,tagdata))
  cs.append(chunk(0x2005,pack('<HhhBHh5xHH',0,0,0,255,2,0,36,86)+zlib.compress(im.tobytes(),9)))
  data=b''.join(cs);payload.append(pack('<IHHH2xI',len(data)+16,0xF1FA,len(cs),ms,0)+data)
 data=b''.join(payload);header=bytearray(128);pack_into('<IHHHHHIH',header,0,len(data)+128,0xA5E0,total,36,86,32,1,60);header[34:36]=bytes((1,1))
 (OUT/'Alisa_polished.aseprite').write_bytes(header+data)
 # Independently decompress all native cels and compare to the PNG export.
 doc=header+data;p=128
 for n,(im,ms) in enumerate(frames):
  length,magic,num,dur=unpack_from('<IHHH',doc,p);end=p+length;p+=16;rgba=None
  assert magic==0xF1FA and dur==ms
  for _ in range(num):
   size,kind=unpack_from('<IH',doc,p);raw=doc[p+6:p+size];p+=size
   if kind==0x2005:rgba=zlib.decompress(raw[20:])
  assert p==end and rgba==im.tobytes()
  assert sheet.crop((n%16*36,n//16*86,n%16*36+36,n//16*86+86)).tobytes()==rgba
 assert p==len(doc)
 print('Asset verification:',total,'frames,',len(tags),'clips,8 directions; PNG/Aseprite exact.',flush=True)

# Round the eight-direction path without resetting gait at corners.
screen=[(112,210),(208,210),(256,210-48*CAM),(256,182-48*CAM),(208,182-96*CAM),
        (112,182-96*CAM),(64,182-48*CAM),(64,210-48*CAM),(112,210),(160,210)]
world=np.array([(x,y/CAM) for x,y in screen],float)
points=[]
for i in range(len(world)-1):
 p0=world[i-1] if i else world[0]-(world[1]-world[0])
 p1=world[i];p2=world[i+1];p3=world[i+2] if i+2<len(world) else world[-1]+(world[-1]-world[-2])
 for u in np.linspace(0,1,100,endpoint=False):
  points.append(.5*((2*p1)+(-p0+p2)*u+(2*p0-5*p1+4*p2-p3)*u*u+(-p0+3*p1-3*p2+p3)*u*u*u))
points.append(world[-1]);PATH=np.array(points)
LENGTHS=np.r_[0,np.cumsum(np.linalg.norm(np.diff(PATH,axis=0),axis=1))]
LENGTH=float(LENGTHS[-1])
SPEED=32.
WALK_DUR=math.ceil((LENGTH/SPEED+.5)/.02)*.02
INTRO=1.44;WALK_END=INTRO+WALK_DUR
SETTLE=.40;TURN=.72;READY=.48;ENTER=.84;DANCE=8.;EXIT=.84;ENDIDLE=2.88
DANCE_START=WALK_END+SETTLE+TURN+READY+ENTER
DANCE_END=DANCE_START+DANCE
TOTAL=round((DANCE_END+EXIT+ENDIDLE)*1000)
TOTAL=math.ceil(TOTAL/20)*20

def smooth(x):x=max(0.,min(1.,x));return x*x*(3-2*x)
def distance(t):
 e=.5;dur=WALK_DUR
 if t<e:d=.5*t*t/e;speed=t/e
 elif t<=dur-e:d=t-e/2;speed=1
 else:d=dur-e-.5*(dur-t)**2/e;speed=(dur-t)/e
 return max(0,min(LENGTH,d/(dur-e)*LENGTH)),max(0,min(1,speed))

def at_distance(d):
 j=min(len(PATH)-2,max(0,bisect.bisect_right(LENGTHS,d)-1));f=(d-LENGTHS[j])/max(.0001,LENGTHS[j+1]-LENGTHS[j])
 p=PATH[j]*(1-f)+PATH[j+1]*f
 delta=PATH[min(j+2,len(PATH)-1)]-PATH[max(0,j-1)]
 angle=math.atan2(-delta[0],delta[1])%math.tau
 view=V[int(math.floor(angle/math.tau*8+.5))%8]
 return (float(p[0]),float(p[1]*CAM)),view
PHASE_END=LENGTH/STRIDE*math.tau

def state(ms):
 t=ms/1000
 if t<INTRO:
  order=('down_left','down','down_right','right')
  view='down_left' if t<.72 else order[min(3,int((t-.72)/.18))]
  return screen[0],view,0.,0.,0.
 if t<WALK_END:
  d,amount=distance(t-INTRO);pos,view=at_distance(d)
  return pos,view,d/STRIDE*math.tau,amount,0.
 pos=(160.,210.)
 local=t-WALK_END
 if local<SETTLE:
  return pos,'right',PHASE_END,0.,0.
 local-=SETTLE
 if local<TURN:
  # Three actual adjacent angular drawings; the body rig keeps its scale.
  order=('right','down_right','down','down_left')
  return pos,order[min(3,int(local/TURN*4))],PHASE_END,0.,0.
 local-=TURN
 if local<READY:return pos,'down_left',PHASE_END,0.,0.
 local-=READY
 if local<ENTER:
  w=smooth(local/ENTER)
  u=local/ENTER
  return pos,'down_left',PHASE_END+math.tau*ENTER*(u**3-.5*u**4),0.,w
 local-=ENTER
 phase0=PHASE_END+math.tau*ENTER*.5
 if local<DANCE:return pos,'down_left',phase0+math.tau*local,0.,1.
 local-=DANCE
 if local<EXIT:
  w=1-smooth(local/EXIT)
  u=local/EXIT
  return pos,'down_left',phase0+math.tau*DANCE+math.tau*EXIT*(u-u**3+.5*u**4),0.,w
 return pos,'down_left',phase0+math.tau*(DANCE+EXIT*.5),0.,0.

@lru_cache(256)
def pose_cached(view,phase_bin,amount_bin,dance_bin,time_bin):
 return core.character(view,phase_bin*.02,amount_bin*.025,dance_bin*.025,time_bin*.02)
def render(ms):
 pos,view,ph,amount,dance=state(ms)
 # Native output is sampled at50fps; phase remains continuous across turns.
 pose=pose_cached(view,round(ph/.02),round(amount/.025),round(dance/.025),round(ms/20))
 x,y=round(pos[0])-18,round(pos[1])-85
 box=pose.getbbox();assert box and x+box[0]>=0 and y+box[1]>=0 and x+box[2]<=320 and y+box[3]<=240
 out=BG.copy();shadow=Image.new('RGBA',(320,240));d=ImageDraw.Draw(shadow)
 d.ellipse((pos[0]-12-4*dance,pos[1]-2,pos[0]+12+4*dance,pos[1]+2),fill=(16,19,29,60))
 out.alpha_composite(shadow);out.alpha_composite(pose,(x,y))
 return out.convert('RGB')

MAT=np.array([[65.481,128.553,24.966],[-37.797,-74.203,112.0],[112.0,-93.786,-18.214]],np.float32)/255
def yuv(im):
 a=np.rint(np.asarray(im).astype(np.float32)@MAT.T+[16,128,128]).astype(np.uint8)
 return (a[:,:,0].repeat(4,0).repeat(4,1),a[:,:,1].repeat(2,0).repeat(2,1),a[:,:,2].repeat(2,0).repeat(2,1))
def planes():
 for t in range(0,TOTAL,20):yield yuv(render(t))
def review():
 times=[0]+[round((INTRO+WALK_DUR*i/8)*1000) for i in range(1,9)]+[round(DANCE_START*1000+750),round(DANCE_END*1000+400),TOTAL-500]
 board=Image.new('RGB',(320*4,260*3),(40,42,50));d=ImageDraw.Draw(board)
 for i,t in enumerate(times):
  t=min(t,TOTAL-20);im=render(t);x=i%4*320;y=i//4*260;board.paste(im,(x,y));d.text((x+5,y+243),f'{t/1000:.2f}s {state(t)[1]}',fill='white')
 board.save(R/'scene_qa.png')
 render(round(DANCE_START*1000+700)).resize((1280,960),Image.Resampling.NEAREST).save(OUT/'Alisa_polished_poster.png')
 data={'durationMs':TOTAL,'nativeSprite':[36,86],'fps':50,'walkDirections':list(V),'walkStart':INTRO,'walkEnd':WALK_END,'danceStart':DANCE_START,'danceEnd':DANCE_END,'phaseDriver':'travelled planar distance','strideWorldPixels':STRIDE,'diagonalSpeedNormalized':True,'imageMorphing':False}
 (OUT/'Alisa_polished_timing.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 views={state(t)[1] for t in range(int(INTRO*1000),int(WALK_END*1000),20)}
 assert views==set(V),views
 # Every state uses the same source parts and rig, including both blends.
 for boundary in (WALK_END,WALK_END+SETTLE,WALK_END+SETTLE+TURN,DANCE_START,DANCE_END,DANCE_END+EXIT):
  before=state(round(boundary*1000)-1);after=state(round(boundary*1000)+1)
  assert abs(before[4]-after[4])<.02
 print('Scene:',TOTAL/1000,'s,8 headings, phasefromdistance, no imagemorph. Dance',DANCE_START,DANCE_END,flush=True)

def verify_video(p):
 count=0;err=0
 for n,(t,planes_actual) in enumerate(decode_reference(p,raw=True)):
  assert abs(t-n*.02)<1e-6
  if n%50==0:
   expect=yuv(render(n*20))
   for a,b in zip(expect,planes_actual):err=max(err,int(np.abs(a.astype(np.int16)-b.astype(np.int16)).max()))
  count+=1
 assert count==TOTAL//20 and err<=6
 print('Decoded',count,'frames; max sampled YUVerror',err,flush=True)

if __name__=='__main__':
 import sys
 export();review()
 if '--render' in sys.argv:
  p=OUT/'Alisa_polished_scene.mp4';encode(planes(),p,1280,960,100,[2]*(TOTAL//20));verify_video(p)
