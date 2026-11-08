
from pathlib import Path
import math,json,zlib
from struct import pack,pack_into
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
R=Path(__file__).resolve().parent
P=R.parents[2]
OUT=R.parent;OUT.mkdir(exist_ok=True)
AT=Image.open(P/'recolor/blue_eyes/Altushka_blue_atlas.png').convert('RGBA')
SIZE=(36,86)
# Ten authored silhouettes: contact, settle, support, push, recovery, reach.
# The toes of the planted leg advance 19px locally over the stance;
# the soles recede5px, cancelling scene translation(-38,+10)px/s.
LEG=[
[(18,55),(23,56),(21,63),(18,70),(12,80),(11,82),(11,85),(4,85),(3,84),(3,83),(5,81),(6,79),(12,67),(15,59)],
[(18,56),(23,57),(22,64),(20,70),(15,79),(15,84),(8,84),(7,83),(7,82),(10,80),(12,76),(13,69),(14,62)],
[(18,57),(23,57),(22,64),(21,70),(18,78),(18,83),(11,83),(10,82),(10,81),(13,79),(14,75),(14,69),(15,62)],
[(18,56),(23,56),(23,64),(22,72),(22,77),(22,82),(15,82),(14,81),(14,80),(17,78),(17,70),(16,63)],
[(18,54),(23,55),(26,63),(26,71),(26,76),(26,81),(19,81),(18,80),(18,79),(21,77),(21,72),(20,65),(17,60)],
[(18,55),(23,55),(28,64),(29,72),(30,75),(28,79),(25,80),(23,80),(22,79),(22,78),(25,75),(24,72),(22,67),(18,61)],
[(18,56),(23,57),(26,63),(26,68),(31,73),(32,77),(29,79),(25,79),(25,77),(27,75),(22,73),(20,69),(17,62)],
[(18,57),(23,57),(22,63),(18,67),(23,72),(25,75),(24,78),(18,78),(17,76),(19,74),(13,70),(11,66),(14,61)],
[(18,56),(23,56),(20,62),(15,68),(17,76),(18,80),(10,80),(10,78),(12,76),(10,70),(8,66),(11,61)],
[(18,54),(23,56),(19,62),(14,68),(14,79),(14,83),(6,83),(6,81),(9,79),(9,70),(8,67),(12,60)]
]
SHADE=[
[(21,58),(23,58),(20,65),(17,72),(11,82),(9,82),(15,70),(18,63)],
[(21,59),(23,59),(21,65),(20,72),(15,80),(13,80),(17,70),(18,64)],
[(21,59),(23,59),(22,65),(21,71),(18,79),(16,80),(18,69),(18,63)],
[(21,58),(23,58),(23,65),(22,76),(22,79),(20,79),(20,68),(19,62)],
[(21,56),(23,56),(26,64),(26,77),(24,78),(23,69),(21,64)],
[(21,57),(23,57),(28,65),(29,74),(28,77),(26,76),(25,68),(22,64)],
[(21,58),(23,59),(26,65),(25,69),(30,74),(29,76),(27,74),(22,71),(21,66)],
[(21,59),(23,59),(20,65),(18,67),(23,73),(23,75),(21,74),(14,69),(14,66),(17,62)],
[(21,58),(23,58),(19,64),(15,68),(17,77),(15,78),(12,70),(11,66),(14,62)],
[(21,57),(23,57),(18,64),(14,69),(14,80),(12,81),(12,68),(13,64)]
]
NECK_DX=(-1,0,1,2,3,3,2,1,0,-1)

def source(i):
 return AT.crop((i%10*36,i//10*86,i%10*36+36,i//10*86+86))

def leg(i,far=False):
 im=Image.new('RGBA',SIZE);d=ImageDraw.Draw(im)
 points=LEG[i%10]
 d.polygon(points,fill=(43,43,48,255) if far else (55,55,60,255),outline=(2,2,2,255))
 shade=Image.new('RGBA',SIZE);sd=ImageDraw.Draw(shade)
 sd.polygon(SHADE[i%10],fill=(28,28,33,255) if far else (43,43,48,255))
 a=np.array(shade);base=np.array(im);a[base[:,:,3]==0]=0;im.alpha_composite(Image.fromarray(a))
 # The exposed thigh is painted within the silhouette, below the skirt.
 a=np.array(im);yy,xx=np.indices((86,36))
 m=(a[:,:,3]>0)&(yy<60)&(a[:,:,:3].max(2)>3)
 a[m,:3]=(247,186,188) if far else (255,242,231)
 im=Image.fromarray(a)
 # A two-tone shoe top follows the individually drawn boot silhouette.
 a=np.array(im);mask=a[:,:,3]>0
 sole=max(y for x,y in points);low=(yy>=sole-1)&mask&(a[:,:,:3].max(2)>3)
 a[low,:3]=(24,24,29) if far else (34,34,38)
 im=Image.fromarray(a)
 if far:
  dst=Image.new('RGBA',SIZE);dst.paste(im,(-3,-1));im=dst
 return im

def upper(i):
 raw=np.array(source(i));rgb=raw[:,:,:3].astype(int);yy,xx=np.indices((86,36))
 cloth=(yy>=41)&(yy<=61)&(raw[:,:,3]>0)&(rgb.min(2)>145)&(rgb.max(2)-rgb.min(2)<38)&(rgb[:,:,2]>=rgb[:,:,0]-5)
 keep=(yy<50)|cloth
 raw[~keep]=0
 out=Image.new('RGBA',SIZE);out.paste(Image.fromarray(raw),(NECK_DX[i],0))
 return out

def frame(i):
 out=Image.new('RGBA',SIZE)
 out.alpha_composite(leg((i+5)%10,True))
 # A continuous hip/thigh fill stays underneath the untouched skirt pixels.
 hip=Image.new('RGBA',SIZE);d=ImageDraw.Draw(hip)
 d.polygon([(12,47),(23,47),(25,51),(24,57),(20,60),(15,59),(12,55)],fill=(247,186,188,255))
 out.alpha_composite(hip)
 out.alpha_composite(leg(i,False))
 out.alpha_composite(upper(i))
 return out

FRAMES=[frame(i) for i in range(10)]

def assets():
 atlas=Image.new('RGBA',(360,86))
 for i,im in enumerate(FRAMES):atlas.paste(im,(36*i,0))
 atlas.save(OUT/'Alisa_walk_study_atlas.png',optimize=True)
 frames=[]
 def chunk(k,b):return pack('<IH',len(b)+6,k)+b
 for n,im in enumerate(FRAMES):
  cs=[]
  if not n:
   s='Алиса'.encode('utf-8');cs.append(chunk(0x2004,pack('<6HB3xH',3,0,0,0,0,0,255,len(s))+s))
   name=b'walk_down_left';tags=pack('<H8x',1)+pack('<HHBH6x3BBH',0,9,0,0,128,189,225,0,len(name))+name
   cs.append(chunk(0x2018,tags))
  cs.append(chunk(0x2005,pack('<HhhBHh5xHH',0,0,0,255,2,0,36,86)+zlib.compress(im.tobytes(),9)))
  b=b''.join(cs);frames.append(pack('<IHHH2xI',len(b)+16,0xF1FA,len(cs),100,0)+b)
 data=b''.join(frames);header=bytearray(128);pack_into('<IHHHHHIH',header,0,len(data)+128,0xA5E0,10,36,86,32,1,100);header[34:36]=bytes((1,1))
 (OUT/'Alisa_walk_study.aseprite').write_bytes(header+data)
 meta={'frames':[{'filename':f'walk_{i:02}.png','frame':{'x':i*36,'y':0,'w':36,'h':86},'duration':100,'sourceSize':{'w':36,'h':86},'spriteSourceSize':{'x':0,'y':0,'w':36,'h':86},'trimmed':False,'rotated':False} for i in range(10)],
       'meta':{'image':'Alisa_walk_study_atlas.png','size':{'w':360,'h':86},'format':'RGBA8888','scale':'1','frameTags':[{'name':'walk_down_left','from':0,'to':9,'direction':'forward'}]}}
 (OUT/'Alisa_walk_study.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
 bg=Image.new('RGBA',atlas.size,(105,99,112,255));bg.alpha_composite(atlas);bg.resize((2160,516),Image.Resampling.NEAREST).convert('RGB').save(R/'cycle_review.png')
 # View at game scale and at a readable enlarged scale.
 ims=[]
 for _ in range(3):
  for im in FRAMES:
   b=Image.new('RGBA',(60,96),(105,99,112,255));b.alpha_composite(im,(12,4))
   ims.append(b.resize((360,576),Image.Resampling.NEAREST).convert('RGB'))
 palette=Image.fromarray(np.vstack([np.array(i) for i in ims[:10]])).quantize(colors=240,method=Image.Quantize.MEDIANCUT)
 ims=[i.quantize(palette=palette,dither=Image.Dither.NONE) for i in ims]
 ims[0].save(OUT/'Alisa_walk_study.gif',save_all=True,append_images=ims[1:],duration=100,loop=0,disposal=2)
 print('Source anchors:',NECK_DX,'nativeframes',len(FRAMES),flush=True)

if __name__=='__main__':assets()
