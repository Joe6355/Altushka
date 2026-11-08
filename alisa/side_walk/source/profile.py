"""Native 36x86 side-view cels. Integer pixel layers and authored leg contours."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageOps

R=Path(__file__).resolve().parent
P=R.parents[2]
OUT=R.parent
SIZE=(36,86)
PALETTE=[
 (2,2,2),(24,24,29),(34,34,38),(43,43,48),(55,55,60),
 (70,70,78),(139,139,150),(164,164,174),(190,190,200),
 (213,213,223),(232,232,239),(244,244,248),(255,255,255),
 (255,242,231),(247,186,188),(229,145,158),(212,112,135),
 (55,183,226),(139,232,245),(39,92,128),
]
BASE=Image.open(R/'Profile_native.png').convert('RGBA')

def blank():return Image.new('RGBA',SIZE)
def shift(im,x=0,y=0):
 out=blank();out.paste(im,(x,y));return out

# Match the original vertical landmarks: crown at8px, chin at27px,
# waist at44px, skirt at44..55px. The curl and ground stay at0 and85.
a=np.asarray(BASE).copy()
b=np.zeros_like(a);b[:6]=a[:6];b[8:56]=a[6:54]
b[6,21]=(*PALETTE[7],255);b[7,21]=(*PALETTE[7],255)
MASTER=Image.fromarray(b)

def head():
 arr=np.asarray(MASTER).copy();arr[30:]=0
 # Large authored hair clusters replace the draft's tiny color speckles.
 yy,xx=np.indices((86,36));rgb=arr[:,:,:3].astype(int)
 hair=(yy>=8)&(yy<=29)&(arr[:,:,3]>0)&(rgb.min(2)>95)&(rgb.max(2)-rgb.min(2)<18)&~((yy>=19)&(xx>=23))
 paint=blank();d=ImageDraw.Draw(paint)
 d.rectangle((0,0,35,85),fill=(*PALETTE[10],255))
 d.polygon([(6,17),(10,14),(12,18),(10,23),(12,27),(16,29),(13,29),(9,25),(8,22),(6,21)],fill=(*PALETTE[8],255))
 d.polygon([(9,23),(12,22),(15,25),(17,28),(15,29),(12,28),(10,26)],fill=(*PALETTE[6],255))
 d.polygon([(13,10),(20,9),(25,11),(22,13),(17,13),(14,16),(12,16),(12,14)],fill=(*PALETTE[12],255))
 d.polygon([(11,15),(15,12),(15,16),(13,19),(12,23),(14,25),(15,26),(12,26),(10,23),(11,20)],fill=(*PALETTE[9],255))
 d.polygon([(17,14),(19,13),(18,18),(17,20),(17,25),(19,27),(16,27),(15,24),(15,21)],fill=(*PALETTE[8],255))
 d.polygon([(20,12),(23,13),(24,16),(27,18),(28,21),(25,21),(24,18),(22,17),(21,15)],fill=(*PALETTE[9],255))
 arr[hair]=np.asarray(paint)[hair]
 arr[21,24]=(*PALETTE[18],255)
 # Preserve the original profile face and its single forward-looking eye.
 return Image.fromarray(arr)

HEAD=head()
t=np.asarray(MASTER).copy();t[:30]=0;t[46:]=0
yy,xx=np.indices((86,36));rgb=t[:,:,:3].astype(int)
white=(yy>=44)&(rgb.min(2)>95)&(rgb.max(2)-rgb.min(2)<18)
t[white]=0
TORSO=Image.fromarray(t)

def torso(drop=0):
 if not drop:return TORSO.copy()
 # One deliberately edited lower bust cel, with the arm/hand kept in place.
 out=TORSO.copy();d=ImageDraw.Draw(out)
 patch=TORSO.crop((22,33,30,41))
 d.rectangle((22,33,30,41),fill=(0,0,0,0))
 d.polygon([(21,33),(24,34),(25,38),(24,41),(21,42)],fill=(*PALETTE[3],255))
 out.alpha_composite(patch,(22,33+drop))
 out.alpha_composite(patch.crop((0,0,8,1)),(22,33))
 return out

def skirt():
 arr=np.asarray(MASTER).copy();yy,xx=np.indices((86,36));rgb=arr[:,:,:3].astype(int)
 white=(yy>=44)&(yy<=55)&(arr[:,:,3]>0)&(rgb.min(2)>95)&(rgb.max(2)-rgb.min(2)<18)
 edge=np.zeros_like(white)
 edge[1:]|=white[:-1];edge[:-1]|=white[1:];edge[:,1:]|=white[:,:-1];edge[:,:-1]|=white[:,1:]
 black=(rgb.max(2)<10)&edge
 hem=(yy>=54)&(yy<=55)&edge&(rgb[:,:,0]>170)&(rgb[:,:,0]-rgb[:,:,1]>20)
 arr[~(white|black|hem)]=0
 return Image.fromarray(arr)

SKIRT=skirt()

def skirt_pose(n):
 """Three edited hem positions, anchored to the unchanged waistband."""
 if n==0:return SKIRT.copy()
 out=blank()
 offsets=([0,0,0,0,0,-1,-1,-1,-1,-1,-1,-1] if n==1 else
          [0,0,0,0,-1,-1,-1,-2,-2,-2,-2,-2])
 for y,dx in zip(range(44,56),offsets):
  out.alpha_composite(SKIRT.crop((0,y,36,y+1)),(dx,y))
 return out

SKIRTS=[skirt_pose(i) for i in range(3)]
BOB=(0,1,2,1,0,0,1,2,1,0)
CHEST=(0,0,1,1,0,0,0,1,1,0)
CLOTH=(1,1,2,2,1,0,1,2,2,1)

# Contact, compression, passing, extension, toe-off, recovery, and reach.
# Planted toes0..5 are34,30,26,22,18,14. Root+4px/cel cancels this exactly.
LEG=[
 [(17,54),(23,55),(26,64),(27,71),(29,81),(33,82),(34,83),(34,85),(26,85),(25,83),(24,76),(22,69),(18,64),(16,59)],
 [(17,55),(23,56),(25,65),(24,71),(25,81),(29,82),(30,83),(30,85),(22,85),(21,83),(20,74),(20,68),(17,63),(16,59)],
 [(17,56),(23,57),(24,65),(22,72),(21,81),(25,82),(26,83),(26,85),(18,85),(17,83),(17,74),(18,67),(16,62)],
 [(17,55),(23,56),(22,64),(19,71),(17,81),(21,82),(22,83),(22,85),(14,85),(13,83),(13,76),(14,69),(15,62)],
 [(17,54),(23,55),(21,63),(17,70),(13,81),(17,82),(18,83),(18,85),(10,85),(9,83),(9,78),(11,70),(14,62)],
 [(17,54),(23,55),(20,62),(14,69),(9,80),(13,82),(14,83),(14,85),(6,85),(5,83),(6,79),(9,70),(13,62)],
 [(17,55),(23,56),(20,63),(14,67),(11,74),(12,78),(14,79),(13,81),(6,81),(5,79),(6,74),(8,68),(12,63)],
 [(17,56),(23,57),(22,62),(19,66),(14,69),(12,72),(15,74),(15,77),(8,77),(6,75),(8,71),(11,67),(13,64)],
 [(17,55),(23,56),(26,62),(27,65),(23,70),(22,73),(25,75),(25,78),(18,78),(16,76),(16,72),(19,66),(17,62)],
 [(17,54),(23,55),(27,62),(28,67),(28,76),(31,79),(33,80),(33,83),(25,83),(24,81),(23,77),(22,69),(18,63),(16,59)]
]
SHADE=[
 [(21,58),(23,58),(26,65),(27,74),(29,81),(27,82),(24,74),(23,69),(20,64)],
 [(21,59),(23,60),(25,66),(24,73),(25,81),(23,82),(22,73),(22,68),(20,64)],
 [(21,60),(23,60),(24,66),(22,73),(21,81),(19,82),(19,74),(20,68),(19,64)],
 [(21,59),(23,59),(21,66),(19,73),(17,81),(15,82),(16,73),(17,66),(18,62)],
 [(21,58),(23,58),(20,65),(16,73),(13,81),(11,82),(12,75),(14,68),(17,62)],
 [(21,58),(23,58),(19,64),(13,72),(9,81),(7,82),(8,76),(11,68),(16,61)],
 [(21,59),(23,59),(19,65),(14,69),(11,75),(12,79),(9,79),(8,76),(10,68),(16,63)],
 [(21,60),(23,60),(21,64),(18,68),(13,71),(12,74),(10,74),(11,69),(15,65)],
 [(21,59),(23,59),(26,64),(24,68),(21,73),(23,76),(20,76),(19,73),(20,68),(22,65)],
 [(21,58),(23,58),(27,64),(28,70),(28,77),(31,81),(28,81),(25,77),(24,69),(21,64)]
]

def leg(phase,far=False):
 i=phase%10;out=blank();d=ImageDraw.Draw(out)
 d.polygon(LEG[i],fill=(*PALETTE[3 if far else 4],255),outline=(*PALETTE[0],255))
 shade=blank();ImageDraw.Draw(shade).polygon(SHADE[i],fill=(*PALETTE[1 if far else 3],255))
 a=np.asarray(out).copy();sh=np.asarray(shade).copy();sh[a[:,:,3]==0]=0
 out.alpha_composite(Image.fromarray(sh));a=np.asarray(out).copy()
 yy,xx=np.indices((86,36));color=a[:,:,:3].max(2)>3
 skin=(a[:,:,3]>0)&(yy<60+BOB[i])&color
 a[skin,:3]=PALETTE[14 if far else 13]
 sole=max(p[1] for p in LEG[i]);shoe=(a[:,:,3]>0)&(yy>=sole-2)&color
 a[shoe,:3]=PALETTE[1 if far else 2]
 out=Image.fromarray(a)
 return shift(out,-2,-1) if far else out

LAYERS=('far_leg','hips','near_leg','skirt','torso','head')

def head_pose(phase):
 # The curl trails by one pixel; face/eye pixels are never changed.
 out=HEAD.copy()
 if phase in (2,3,7,8):
  curl=HEAD.crop((0,0,36,6))
  ImageDraw.Draw(out).rectangle((0,0,35,5),fill=(0,0,0,0))
  out.alpha_composite(curl,(-1,0))
 return shift(out,0,BOB[phase])

def walk_layers(i):
 i%=10;hip=blank()
 ImageDraw.Draw(hip).polygon([(17,51+BOB[i]),(24,51+BOB[i]),(25,58+BOB[i]),(20,62+BOB[i]),(16,58+BOB[i])],fill=(*PALETTE[14],255))
 return [leg(i+5,True),hip,leg(i),shift(SKIRTS[CLOTH[i]],0,BOB[i]),shift(torso(CHEST[i]),0,BOB[i]),head_pose(i)]

idle_lower=np.asarray(BASE).copy();idle_lower[:54]=0
IDLE_LOWER=Image.fromarray(idle_lower)

def idle_layers(breath=0):
 return [blank(),blank(),IDLE_LOWER.copy(),SKIRT.copy(),torso(breath),HEAD.copy()]

def flatten(layers):
 out=blank()
 for im in layers:out.alpha_composite(im)
 return out

WALK_LAYERS=[walk_layers(i) for i in range(10)]
WALK=[flatten(layers) for layers in WALK_LAYERS]
IDLE_LAYERS=[idle_layers(i) for i in (0,1,1,0)]
IDLE=[flatten(layers) for layers in IDLE_LAYERS]
IDLE_MS=(600,300,600,900)

def mirror_layers(layers):return [ImageOps.mirror(im) for im in layers]

if __name__=='__main__':
 bg=Image.new('RGBA',(36*10,86*2),(105,99,112,255))
 for n,im in enumerate(WALK):
  bg.alpha_composite(im,(36*n,0));bg.alpha_composite(ImageOps.mirror(im),(36*n,86))
 bg.resize((1800,860),Image.Resampling.NEAREST).convert('RGB').save(R/'cycle_review.png')
 comp=Image.new('RGBA',(36*3,96),(105,99,112,255))
 orig=Image.open(P/'recolor/blue_eyes/Altushka_blue_atlas.png').convert('RGBA').crop((144,0,180,86))
 comp.alpha_composite(orig,(0,5));comp.alpha_composite(IDLE[0],(36,5));comp.alpha_composite(WALK[0],(72,5))
 comp.resize((864,768),Image.Resampling.NEAREST).save(R/'model_review.png')
 print('Side walk:',len(WALK),'native cels;',SIZE)
