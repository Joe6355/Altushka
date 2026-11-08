"""Rear and rear-diagonal native cels, matching the approved36x86 side view."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageOps
from prepare_native import PALETTE

R=Path(__file__).resolve().parent
SIZE=(36,86)
BOB=(0,1,2,1,0,0,1,2,1,0)
SWAY=(0,0,-1,-1,0,0,0,1,1,0)

def blank():return Image.new('RGBA',SIZE)
def shift(im,x=0,y=0):
 out=blank();out.paste(im,(x,y));return out
def flatten(layers):
 out=blank()
 for im in layers:out.alpha_composite(im)
 return out
def mirrored(layers):return [ImageOps.mirror(im) for im in layers]

# Left leg viewed directly from behind. Heel75..85 during stance0..5
# cancels a -2px/cel root advance. The returning heel visibly lifts.
N_LEG=[
 [(9,53),(16,53),(16,61),(15,65),(15,70),(16,73),(16,75),(9,75),(8,74),(8,72),(9,70),(9,66),(8,61),(8,57)],
 [(9,54),(16,54),(16,62),(15,67),(15,72),(16,75),(16,77),(9,77),(8,76),(8,74),(9,72),(9,67),(8,62),(8,58)],
 [(9,55),(16,55),(16,63),(15,69),(15,74),(16,77),(16,79),(9,79),(8,78),(8,76),(9,74),(9,69),(8,63),(8,59)],
 [(9,54),(16,54),(17,62),(16,69),(15,76),(16,79),(16,81),(9,81),(8,80),(8,78),(9,76),(9,69),(8,63),(8,58)],
 [(9,53),(16,53),(17,61),(17,69),(15,78),(16,81),(16,83),(9,83),(8,82),(8,80),(9,78),(10,70),(9,63),(8,58)],
 [(9,53),(16,53),(17,61),(17,70),(15,80),(16,83),(16,85),(9,85),(8,84),(8,82),(9,80),(10,71),(9,64),(8,59)],
 [(9,54),(16,54),(16,61),(14,67),(13,75),(16,80),(16,83),(10,83),(9,81),(9,78),(8,74),(8,67),(8,61),(8,58)],
 [(9,55),(16,55),(16,61),(13,66),(12,70),(16,76),(17,79),(10,79),(9,77),(9,74),(7,70),(7,65),(8,61),(8,58)],
 [(9,54),(16,54),(16,60),(14,64),(13,68),(16,73),(17,76),(10,76),(9,74),(9,71),(8,67),(8,62),(8,58)],
 [(9,53),(16,53),(16,60),(15,64),(14,68),(15,71),(16,74),(9,74),(8,72),(9,69),(9,65),(8,61),(8,57)]
]
N_SHADE=[
 [(14,60),(14,65),(13,70)],[(14,61),(14,67),(13,72)],
 [(14,62),(14,69),(13,74)],[(15,61),(14,69),(13,76)],
 [(15,60),(15,69),(13,78)],[(15,60),(15,70),(13,80)],
 [(14,60),(12,67),(11,75),(14,80)],[(14,61),(11,66),(10,70),(14,76)],
 [(14,60),(12,65),(11,68),(14,73)],[(14,60),(13,65),(12,69),(13,71)]
]
N_HEEL=(75,77,79,81,83,85,83,79,76,74)

# Camera-near leg for walking northeast. Authored toes0..5 advance locally
# (-19,+5)px, cancelling (+19,-5)px of root movement over the stance.
NE_LEG=[
 [(18,53),(24,54),(25,61),(27,67),(29,74),(32,76),(34,77),(34,79),(31,80),(27,80),(26,78),(24,72),(21,66),(17,61)],
 [(18,54),(24,55),(25,62),(25,68),(25,75),(29,77),(30,78),(30,80),(27,81),(23,81),(22,79),(21,73),(20,67),(17,62)],
 [(18,55),(24,56),(25,63),(23,69),(21,76),(25,78),(26,79),(26,81),(23,82),(19,82),(18,80),(18,75),(19,69),(17,63)],
 [(18,54),(24,55),(24,63),(21,69),(18,77),(22,79),(23,80),(23,82),(20,83),(16,83),(15,81),(15,77),(17,69),(16,63)],
 [(18,53),(24,54),(23,62),(19,69),(14,78),(18,80),(19,81),(19,83),(16,84),(12,84),(11,82),(12,78),(14,70),(16,63)],
 [(18,53),(24,54),(22,62),(17,69),(10,79),(14,81),(15,82),(15,84),(12,85),(8,85),(7,83),(8,79),(11,70),(15,62)],
 [(18,54),(24,55),(22,61),(16,66),(12,74),(12,77),(15,78),(15,80),(12,82),(7,82),(6,80),(8,77),(9,72),(11,65),(15,61)],
 [(18,55),(24,56),(23,61),(19,65),(13,69),(13,72),(17,74),(17,76),(14,78),(9,78),(8,76),(9,73),(8,69),(12,64),(15,61)],
 [(18,54),(24,55),(26,60),(27,64),(22,69),(22,71),(26,73),(26,75),(23,77),(18,77),(17,75),(17,71),(19,65),(17,61)],
 [(18,53),(24,54),(27,60),(29,65),(28,71),(28,74),(32,75),(32,77),(29,79),(24,79),(23,77),(23,73),(23,68),(20,63),(17,60)]
]
NE_SHADE=[
 [(22,59),(24,64),(27,70),(28,76),(31,78)],
 [(22,60),(23,65),(23,71),(24,77),(27,79)],
 [(22,61),(23,65),(21,71),(20,78),(23,80)],
 [(22,60),(22,65),(19,71),(17,79),(20,81)],
 [(22,59),(21,65),(17,71),(13,80),(16,82)],
 [(22,59),(20,65),(15,72),(9,81),(12,83)],
 [(22,60),(20,64),(14,69),(12,75),(11,79)],
 [(22,61),(21,64),(16,68),(11,70),(12,75)],
 [(22,60),(25,63),(24,65),(20,70),(20,74)],
 [(22,59),(26,63),(27,66),(26,72),(26,76)]
]
NE_HEEL=(80,81,82,83,84,85,82,78,77,79)

def paint_leg(points,shade,phase,dim=False,lifted=False):
 im=blank();ImageDraw.Draw(im).polygon(points,fill=(*PALETTE[3 if dim else 4],255),outline=(*PALETTE[0],255))
 sh=blank();ImageDraw.Draw(sh).line(shade,fill=(*PALETTE[1 if dim else 3],255),width=2)
 a=np.asarray(im).copy();s=np.asarray(sh).copy();s[(a[:,:,3]==0)|(a[:,:,:3].max(2)<=3)]=0
 im.alpha_composite(Image.fromarray(s));a=np.asarray(im).copy()
 yy,xx=np.indices((86,36));color=(a[:,:,3]>0)&(a[:,:,:3].max(2)>3)
 a[color&(yy<60+BOB[phase%10]),:3]=PALETTE[14 if dim else 13]
 sole=max(y for x,y in points)
 a[color&(yy>=sole-4),:3]=PALETTE[1 if dim else 2]
 if lifted:a[color&(yy>=sole-2),:3]=PALETTE[2 if dim else 3]
 return Image.fromarray(a)

def n_leg(phase,right=False):
 i=phase%10;im=paint_leg(N_LEG[i],N_SHADE[i],i,right,i>=6)
 return ImageOps.mirror(im) if right else im

def ne_leg(phase,far=False):
 i=phase%10;im=paint_leg(NE_LEG[i],NE_SHADE[i],i,far,i>=6)
 return shift(im,-6,-1) if far else im

def mask_skirt(master):
 a=np.asarray(master).copy();rgb=a[:,:,:3].astype(int);yy,xx=np.indices((86,36))
 white=(yy>=44)&(yy<=56)&(a[:,:,3]>0)&(rgb.min(2)>95)&(rgb.max(2)-rgb.min(2)<18)
 edge=np.zeros_like(white);edge[1:]|=white[:-1];edge[:-1]|=white[1:];edge[:,1:]|=white[:,:-1];edge[:,:-1]|=white[:,1:]
 black=edge&(rgb.max(2)<10)
 hem=(yy>=54)&(yy<=56)&edge&(rgb[:,:,0]>170)&(rgb[:,:,0]-rgb[:,:,1]>20)
 a[~(white|black|hem)]=0
 return Image.fromarray(a)

class Model:
 def __init__(self,name,diagonal=False):
  self.name=name;self.diagonal=diagonal
  self.master=Image.open(R/f'{name}_native.png').convert('RGBA')
  a=np.asarray(self.master).copy();a[30:]=0;self.head=Image.fromarray(a)
  a=np.asarray(self.master).copy();a[:30]=0;a[46:]=0
  yy,xx=np.indices((86,36));rgb=a[:,:,:3].astype(int)
  white=(yy>=44)&(rgb.min(2)>95)&(rgb.max(2)-rgb.min(2)<18);a[white]=0
  self.torso=Image.fromarray(a);self.skirt=mask_skirt(self.master)
  a=np.asarray(self.master).copy();a[:54]=0
  skin=(yy<60)&(a[:,:,3]>0)&(a[:,:,:3].max(2)>3)
  a[skin&(xx<18),:3]=PALETTE[14];a[skin&(xx>=18),:3]=PALETTE[13]
  self.idle_lower=Image.fromarray(a)
  self.idle_layers=[self.idle(b) for b in (0,1,1,0)]
  self.walk_layers=[self.walk(i) for i in range(10)]
  self.start_layers=self.start()
  self.stop_layers=list(reversed(self.start_layers))

 def cloth(self,swing):
  out=blank()
  for y in range(44,57):
   dx=0 if y<48 else (swing if y>=52 else (1 if swing>0 else -1 if swing<0 else 0))
   out.alpha_composite(self.skirt.crop((0,y,36,y+1)),(dx,y))
  return out

 def upper(self,phase=None,breath=0):
  b=0 if phase is None else BOB[phase]
  sway=0 if phase is None else SWAY[phase]
  torso=self.torso.copy()
  if breath:
   a=np.asarray(torso).copy();a[32:40,11:25]=a[33:41,11:25];torso=Image.fromarray(a)
  h=self.head.copy()
  if phase in (2,3,7,8):
   tip=h.crop((0,0,36,6));ImageDraw.Draw(h).rectangle((0,0,35,5),fill=(0,0,0,0))
   h.alpha_composite(tip,(-1 if phase<5 else 1,0))
  swing=0 if phase is None else ((0,-1,-2,-1,0,0,1,2,1,0)[phase])
  if self.diagonal:swing=0 if phase is None else (0,-1,-2,-2,-1,0,-1,-2,-1,0)[phase]
  return [shift(self.cloth(swing),sway,b),shift(torso,sway,b),shift(h,sway,b)]

 def hip(self,phase=0):
  im=blank();x=SWAY[phase];y=BOB[phase];d=ImageDraw.Draw(im)
  points=([(15,51),(25,51),(26,55),(22,57),(16,56)] if self.diagonal else [(9,51),(26,51),(26,55),(22,56),(14,56),(9,55)])
  d.polygon([(px+x,py+y) for px,py in points],fill=(*PALETTE[14],255))
  return im

 def idle(self,breath=0):return [blank(),blank(),self.idle_lower.copy(),*self.upper(breath=breath)]

 def walk(self,i):
  i%=10
  near=ne_leg(i) if self.diagonal else n_leg(i)
  far=ne_leg(i+5,True) if self.diagonal else n_leg(i+5,True)
  return [far,self.hip(i),near,*self.upper(i)]

 def start(self):
  result=[self.idle_layers[0]]
  for n,(phase,up,body) in enumerate(((4,1,0),(2,2,1),(0,1,0))):
   if self.diagonal:
    p=(3,1,0)[n];near=shift(ne_leg(p),0,-up)
    if n<2:
     a=np.asarray(self.idle_lower).copy();a[:,18:]=0;far=Image.fromarray(a)
    else:far=ne_leg(4,True)
   else:
    near=shift(n_leg(phase),0,-up);far=n_leg(5,True)
   result.append([far,self.hip(body),near,*self.upper(body)])
  result.append(self.walk_layers[0])
  return result

BACK=Model('Back')
DIAGONAL=Model('Back_diagonal',True)
IDLE_MS=(600,300,600,900)
MODELS={'back':BACK,'back_right':DIAGONAL}

def clips():
 result=[]
 for direction,model,mirror,pivot,velocity in (
  ('back',BACK,False,18,(0,-20)),
  ('back_right',DIAGONAL,False,18,(38,-10)),
  ('back_left',DIAGONAL,True,17,(-38,-10))):
  for state,layers,ms in (
   ('idle',model.idle_layers,IDLE_MS),('start',model.start_layers,[100]*5),
   ('walk',model.walk_layers,[100]*10),('stop',model.stop_layers,[100]*5)):
   result.append((f'{state}_{direction}',[mirrored(l) for l in layers] if mirror else layers,ms,pivot,velocity if state=='walk' else (0,0)))
 return result

CLIPS=clips()

if __name__=='__main__':
 board=Image.new('RGBA',(360,258),(105,99,112,255))
 for row,ims in enumerate((BACK.walk_layers,DIAGONAL.walk_layers,[mirrored(l) for l in DIAGONAL.walk_layers])):
  for n,layers in enumerate(ims):board.alpha_composite(flatten(layers),(n*36,row*86))
 board.resize((1800,1290),Image.Resampling.NEAREST).convert('RGB').save(R/'cycle_review.png')
 board=Image.new('RGBA',(180,344),(105,99,112,255))
 for row,layers in enumerate((BACK.start_layers,BACK.stop_layers,DIAGONAL.start_layers,DIAGONAL.stop_layers)):
  for n,cel in enumerate(layers):board.alpha_composite(flatten(cel),(36*n,86*row))
 board.resize((900,1720),Image.Resampling.NEAREST).convert('RGB').save(R/'transition_review.png')
