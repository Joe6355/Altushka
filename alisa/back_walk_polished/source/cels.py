"""Native cel polishing: authored contours, foot roll, body counter-motion."""
from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
from PIL import Image,ImageDraw,ImageOps

R=Path(__file__).resolve().parent
SIZE=(36,86)
PALETTE=[(2,2,2),(24,24,29),(34,34,38),(43,43,48),(55,55,60),
 (70,70,78),(139,139,150),(164,164,174),(190,190,200),(213,213,223),
 (232,232,239),(244,244,248),(255,255,255),(255,242,231),(247,186,188),
 (229,145,158),(212,112,135),(55,183,226),(139,232,245),(39,92,128)]
WALK_MS=60
BOB=(0,1,1,2,2,1,1,0)*2
HEAD_BOB=(0,0,1,1,1,1,0,0)*2
PELVIS=(0,-1,-1,-1,0,0,1,1,0,1,1,1,0,0,-1,-1)
SHOULDER=(0,0,0,1,1,0,0,0,0,0,0,-1,-1,0,0,0)
HAIR=(0,0,-1,-1,-1,0,0,0,0,0,1,1,1,0,0,0)

def blank():return Image.new('RGBA',SIZE)
def shift(im,x=0,y=0):
 out=blank();out.paste(im,(x,y));return out
def flatten(layers):
 out=blank()
 for im in layers:out.alpha_composite(im)
 return out
def mirrored(layers):return [ImageOps.mirror(im) for im in layers]
def pixel_round(x):return math.floor(x+.5)

# Per-cel knee edges, knee height, calf edges/height, heel and foot roll.
# These are drawing coordinates, not an IK skeleton. Hip and ankle contours
# retain their native width; both feet share the same boot design in idle/walk.
# kneeL,kneeR,kneeY, calfL,calfR,calfY, heelX,heelY, roll
N_POSES=[
 (10,15,64,10,14,68,12,77,0), (9,14,65,10,14,69,12,78,0),
 (9,14,66,10,14,70,12,79,0), (9,14,67,10,14,71,12,80,0),
 (10,15,68,10,15,72,12,81,0), (10,15,68,10,15,73,12,82,0),
 (10,15,69,10,15,74,12,83,0), (11,16,69,10,15,75,12,84,0),
 (11,16,69,10,15,76,12,85,0), (10,15,68,10,14,75,12,84,1),
 (9,14,67,10,14,73,12,82,2), (9,14,66,10,14,71,13,80,2),
 (9,14,65,10,14,69,13,78,2), (10,15,64,10,14,68,13,76,2),
 (10,15,64,10,14,68,13,75,1), (10,15,64,10,14,68,12,76,1),
]
NE_POSES=[
 (23,27,65,24,28,73,31,81,0), (23,27,66,24,27,73,29,81,0),
 (22,26,66,22,25,74,27,82,0), (21,25,67,20,24,74,25,82,0),
 (20,24,68,18,22,75,23,83,0), (18,23,67,16,20,75,21,83,0),
 (17,22,67,14,18,76,19,84,0), (16,21,66,12,17,76,17,84,0),
 (15,20,66,10,15,77,15,85,0), (15,20,65,10,15,75,14,84,1),
 (15,20,64,11,16,73,14,82,2), (17,22,64,12,17,71,16,80,2),
 (20,25,64,15,20,70,20,78,2), (23,28,64,19,24,70,24,77,2),
 (24,29,65,23,27,71,28,78,1), (24,28,65,25,29,73,30,80,1),
]

def leg(points,diagonal=False,far=False,hip=0,bob=0,heel=None,right=False):
 kl,kr,ky,cl,cr,cy,hx,hy,roll=points
 if heel is not None:
  dx,dy=heel[0]-hx,heel[1]-hy
  cl+=pixel_round(dx*.5);cr+=pixel_round(dx*.5);cy+=pixel_round(dy*.5)
  hx,hy=heel
 ankleX=hx-1 if diagonal else hx
 ankleY=hy-(5 if roll else 4)
 hl,hr=(18+hip,24+hip) if diagonal else (9+hip,16+hip)
 body=[(hl,53+bob),(hr,53+bob),(hr+1,58+bob),(kr,ky-2),(kr,ky+1),
       (cr,cy),(ankleX+1,ankleY+1),(ankleX-1,ankleY+1),(cl,cy),
       (kl,ky+1),(kl-1,ky-2),(hl-1,58+bob)]
 if diagonal:
  shoe=[(hx-1,hy-5),(hx+1,hy-5),(hx+3,hy-3),(hx+3,hy-1),
        (hx+1,hy),(hx-3,hy),(hx-4,hy-1),(hx-3,hy-3)]
 else:
  shoe=[(hx-2,hy-5-roll//2),(hx+2,hy-5-roll//2),(hx+3,hy-3),
        (hx+3,hy-1),(hx+2,hy),(hx-2,hy),(hx-3,hy-1),(hx-3,hy-3)]
 for x,y in body+shoe:
  assert 0<=x<36 and 0<=y<86,(x,y,points)
  if diagonal and far:assert 0<=x-6<36 and 0<=y-1<86
 mask=Image.new('L',SIZE);d=ImageDraw.Draw(mask);d.polygon(body,fill=255);d.polygon(shoe,fill=255)
 m=np.asarray(mask)>0
 interior=m.copy();interior[1:]&=m[:-1];interior[:-1]&=m[1:];interior[:,1:]&=m[:,:-1];interior[:,:-1]&=m[:,1:]
 a=np.zeros((86,36,4),np.uint8);a[m]=(*PALETTE[0],255)
 base=3 if diagonal and far else 4;a[interior]=(*PALETTE[base],255)
 # Inner-leg shading, following the actual silhouette without eating its outline.
 shade=blank();sd=ImageDraw.Draw(shade)
 sd.line([(hr-1,59+bob),(kr-1,ky),(cr-1,cy),(ankleX,ankleY)],fill=(*PALETTE[2 if diagonal and far else 3],255),width=2)
 s=np.asarray(shade);sel=interior&(s[:,:,3]>0);a[sel]=s[sel]
 yy,xx=np.indices((86,36));skin=interior&(yy<60+bob)
 a[skin,:3]=PALETTE[13]
 for y in range(53+bob,60+bob):
  xs=np.flatnonzero(skin[y])
  if len(xs):a[y,xs[-min(2,len(xs)):],:3]=PALETTE[14]
 shoeMask=Image.new('L',SIZE);ImageDraw.Draw(shoeMask).polygon(shoe,fill=255)
 shoeInside=interior&(np.asarray(shoeMask)>0);a[shoeInside,:3]=PALETTE[1 if far and diagonal else 2]
 sole=shoeInside&(yy>=hy-1);a[sole,:3]=PALETTE[1]
 # A small heel cap, and a visible underside only while the heel is raised.
 cap=shoeInside&(abs(xx-hx)<=1)&(yy>=hy-3)&(yy<=hy-2)
 a[cap,:3]=PALETTE[3 if roll else 2]
 if roll==2:a[shoeInside&(yy==hy-3)&(abs(xx-hx)<=1),:3]=PALETTE[3]
 out=Image.fromarray(a)
 if diagonal and far:out=shift(out,-6,-1)
 if right:out=ImageOps.mirror(out)
 return out

def n_leg(i,right=False,hip=None,bob=None,heel=None):
 i%=16
 if hip is None:hip=PELVIS[i]
 if bob is None:bob=BOB[i]
 # Reflection also reflects the hip offset; give both thighs the same sway.
 return leg(N_POSES[i],hip=-hip if right else hip,bob=bob,heel=heel,right=right)

def ne_leg(i,far=False,hip=0,bob=None,heel=None):
 i%=16
 return leg(NE_POSES[i],True,far,hip,BOB[i] if bob is None else bob,heel)

def skirt_mask(im):
 a=np.asarray(im).copy();rgb=a[:,:,:3].astype(int);yy,xx=np.indices((86,36))
 white=(yy>=44)&(yy<=56)&(a[:,:,3]>0)&(rgb.min(2)>95)&(rgb.max(2)-rgb.min(2)<18)
 edge=np.zeros_like(white);edge[1:]|=white[:-1];edge[:-1]|=white[1:];edge[:,1:]|=white[:,:-1];edge[:,:-1]|=white[:,1:]
 black=edge&(rgb.max(2)<10)
 hem=(yy>=54)&(yy<=56)&edge&(rgb[:,:,0]>170)&(rgb[:,:,0]-rgb[:,:,1]>20)
 a[hem,:3]=PALETTE[9];a[~(white|black|hem)]=0
 return Image.fromarray(a)

class Model:
 def __init__(self,name,diagonal=False):
  self.diagonal=diagonal
  master=Image.open(R/f'{name}_native.png').convert('RGBA')
  a=np.asarray(master).copy();a[30:]=0
  # Match the cleaner white clusters of the already-approved profile view.
  old=(a[:,:,:3]==PALETTE[9]).all(2)&(np.indices((86,36))[0]>=8)
  a[old,:3]=PALETTE[10];self.head=Image.fromarray(a)
  a=np.asarray(master).copy();a[:30]=0;a[46:]=0;rgb=a[:,:,:3].astype(int);yy,xx=np.indices((86,36))
  a[(yy>=44)&(rgb.min(2)>95)&(rgb.max(2)-rgb.min(2)<18)]=0;self.torso=Image.fromarray(a)
  self.skirt=skirt_mask(master)
  self.walk_layers=[self.walk(i) for i in range(16)]
  self.idle_layers=[self.idle(b) for b in (0,1,1,0)]
  self.start_layers=self.start();self.stop_layers=self.stop()

 def hip(self,x=0,y=0):
  out=blank();d=ImageDraw.Draw(out)
  p=([(15,51),(25,51),(25,54),(22,56),(16,55)] if self.diagonal else [(9,51),(26,51),(26,54),(22,56),(14,56),(9,54)])
  d.polygon([(px+x,py+y) for px,py in p],fill=(*PALETTE[14],255));return out

 def upper(self,i=None,breath=0,custom=None):
  if i is None:pelvis=shoulder=bob=headbob=lag=0
  else:pelvis,shoulder,bob,headbob,lag=PELVIS[i],SHOULDER[i],BOB[i],HEAD_BOB[i],HAIR[i]
  if custom is not None:pelvis,shoulder,bob,headbob,lag=custom
  torso=blank()
  for y in range(30,46):
   t=min(1,max(0,(y-34)/8));dx=pixel_round(shoulder*(1-t)+pelvis*t)
   torso.alpha_composite(self.torso.crop((0,y,36,y+1)),(dx,y+bob))
  if breath:
   a=np.asarray(torso).copy();a[32:39,12:24]=a[33:40,12:24];torso=Image.fromarray(a)
  # Collar bridges the independently stabilized head and the rolling shoulders.
  collar=blank();ImageDraw.Draw(collar).polygon([(14,28+headbob),(21,28+headbob),(22+shoulder,33+bob),(13+shoulder,33+bob)],fill=(*PALETTE[1],255))
  collar.alpha_composite(torso);torso=collar
  head=blank()
  for y in range(30):
   dx=lag if y>=24 else 0
   if self.diagonal and y>=22:
    # The small cheek edge stays fixed; only the rear hair locks follow through.
    head.alpha_composite(self.head.crop((0,y,24,y+1)),(dx,y+headbob))
    if dx<0:head.alpha_composite(self.head.crop((23,y,24,y+1)),(23,y+headbob))
    head.alpha_composite(self.head.crop((24,y,36,y+1)),(24,y+headbob))
   else:head.alpha_composite(self.head.crop((0,y,36,y+1)),(dx,y+headbob))
  cloth=blank()
  swing=0 if i is None else ((0,0,-1,-1,-1,0,0,0,0,0,1,1,1,0,0,0)[i])
  if self.diagonal:swing=0 if i is None else (0,0,-1,-1,-2,-2,-1,0,0,0,-1,-1,-2,-2,-1,0)[i]
  lift=0 if i is None else (-1 if i in (2,3,4,5) else 1 if i in (10,11,12,13) else 0)
  for x in range(36):
   for y in range(43,58):
    px=self.skirt.getpixel((x,y))
    if not px[3]:continue
    dx=pelvis+(swing if y>=52 else (pixel_round(swing*.5) if y>=48 else 0))
    up=1 if y>=51 and ((lift<0 and x<=15) or (lift>0 and x>=21)) else 0
    xx=x+dx;yy=y+bob-up
    if 0<=xx<36 and 0<=yy<86:cloth.putpixel((xx,yy),px)
  return [cloth,torso,head]

 def idle(self,breath=0):
  if self.diagonal:
   near=ne_leg(5,heel=(22,85),bob=0);far=ne_leg(8,True,bob=0,heel=(17,85))
  else:near=n_leg(8,hip=0,bob=0);far=n_leg(8,True,hip=0,bob=0)
  return [far,self.hip(),near,*self.upper(breath=breath)]

 def walk(self,i):
  if self.diagonal:
   near=ne_leg(i,hip=PELVIS[i]);far=ne_leg(i+8,True,hip=PELVIS[i],bob=BOB[i])
  else:near=n_leg(i);far=n_leg(i+8,True,hip=PELVIS[i],bob=BOB[i])
  return [far,self.hip(PELVIS[i],BOB[i]),near,*self.upper(i)]

 def start(self):
  cels=[self.idle_layers[0]]
  bob=(0,0,1,1,1,1,0,0,0);weight=(0,0,1,1,1,0,0,0,0)
  ne_keys=((5,22,85),(5,23,84),(4,25,82),(3,27,80),(2,29,79),(1,30,79),(0,31,79),(0,31,80),(0,31,81))
  for j in range(1,8):
   b=bob[j];p=weight[j]
   if self.diagonal:
    phase,hx,hy=ne_keys[j];near=ne_leg(phase,hip=p,bob=b,heel=(hx,hy))
    far=ne_leg(8,True,hip=p,bob=b,heel=(16 if j==7 else 17,85))
   else:
    near=n_leg((8+j)%16,hip=p,bob=b);far=n_leg(8,True,hip=p,bob=b)
   cels.append([far,self.hip(p,b),near,*self.upper(custom=(p,0,b,min(b,1),0))])
  cels.append(self.walk_layers[0]);return cels

 def stop(self):
  cels=[self.walk_layers[0]]
  n_heels=(85,84,83,82,82,83,83,84,85)
  ne_near_x=(31,29,27,26,25,24,23,22,22)
  ne_far_x=(9,9,10,11,12,13,12,11,11);ne_far_y=(84,83,81,80,80,81,82,83,84)
  near_phase=(0,1,2,3,4,5,5,5,5);bob=(0,1,1,2,1,1,0,0,0)
  for j in range(1,8):
   b=bob[j];p=(-1 if j<4 else 0)
   if self.diagonal:
    near=ne_leg(near_phase[j],hip=p,bob=b,heel=(ne_near_x[j],81+j//2))
    far=ne_leg((8+j)%16,True,hip=p,bob=b,heel=(ne_far_x[j]+6,ne_far_y[j]+1))
   else:
    near=n_leg(j,hip=p,bob=b);far=n_leg((8+j)%16,True,hip=p,bob=b,heel=(12,n_heels[j]))
   cels.append([far,self.hip(p,b),near,*self.upper(custom=(p,0,b,min(b,1),0))])
  cels.append(self.idle_layers[0]);return cels

BACK=Model('Back')
DIAGONAL=Model('Back_diagonal',True)
IDLE_MS=(600,300,600,900)
START_MS=(100,80,80,60,60,60,60,60,60)
STOP_MS=(60,60,60,80,80,100,100,120,160)

@dataclass
class Clip:
 name:str
 cels:list
 durations:tuple
 pivot:int
 offsets:list
 loop:bool=False
 cycle:tuple=(0,0)

CLIPS=[]
for direction,model,mirror,pivot,step in (
 ('back',BACK,False,18,(0,-1)),
 ('back_right',DIAGONAL,False,18,(2,-.5)),
 ('back_left',DIAGONAL,True,17,(-2,-.5))):
 for state,layers,ms in (('idle',model.idle_layers,IDLE_MS),('start',model.start_layers,START_MS),('walk',model.walk_layers,(60,)*16),('stop',model.stop_layers,STOP_MS)):
  if state=='walk':offsets=[(step[0]*i,step[1]*i) for i in range(16)]
  elif state=='stop':
   if model.diagonal:
    xx=(0,2,4,5,6,7,8,9,9);offsets=[((-x if mirror else x),-.5*i) for i,x in enumerate(xx)]
   else:offsets=[(0,-i) for i in range(9)]
  elif state=='start' and model.diagonal:
   offsets=[((-x if mirror else x),0) for x in (0,0,0,0,0,0,0,1,2)]
  else:offsets=[(0,0)]*len(layers)
  CLIPS.append(Clip(f'{state}_{direction}',[mirrored(l) for l in layers] if mirror else layers,ms,pivot,offsets,state in ('idle','walk'),(step[0]*16,step[1]*16) if state=='walk' else (0,0)))

def turn(name,src,dst,src_pivot=18,dst_pivot=18):
 # Head leads, shoulders follow, then the planted feet pivot into the new stance.
 a=[shift(l,18-src_pivot) for l in src];b=[shift(l,18-dst_pivot) for l in dst]
 phases=[a,[*a[:5],b[5]],[*a[:4],b[4],b[5]],b]
 return Clip(name,phases,(80,80,80,120),18,[(0,0)]*4)

N=BACK.idle_layers[0];NE=DIAGONAL.idle_layers[0];NW=mirrored(NE)
CLIPS.extend((turn('turn_back_right',N,NE),turn('turn_right_back',NE,N),
              turn('turn_back_left',N,NW,18,17),turn('turn_left_back',NW,N,17,18)))
BANK={c.name:c for c in CLIPS}
