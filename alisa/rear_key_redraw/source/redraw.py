"""Four guided drawings -> one8-cel rear cycle, without generated limb geometry."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageOps

R=Path(__file__).resolve().parent
OUT=R.parent
SIZE=(36,86)
PAL=[(2,2,2),(24,24,29),(34,34,38),(43,43,48),(55,55,60),
 (70,70,78),(139,139,150),(164,164,174),(190,190,200),(213,213,223),
 (232,232,239),(244,244,248),(255,255,255),(255,242,231),(247,186,188),
 (229,145,158),(212,112,135),(55,183,226),(139,232,245),(39,92,128)]

def blank():return Image.new('RGBA',SIZE)
def shift(im,y=0):
 out=blank();out.paste(im,(0,y));return out
def flatten(layers):
 out=blank()
 for im in layers:out.alpha_composite(im)
 return out

def import_drawings():
 raw=np.asarray(Image.open(R/'Rear_keys_guided_generated.png').convert('RGBA'))
 mask=raw[:,:,3]>128;ys,xs=np.where(mask)
 top,bottom=int(ys.min()),int(ys.max()+1);cell=raw.shape[1]/4
 scale=(bottom-top)/86
 # One shared anatomical calibration for all poses, matching Alisa's original
 # crown/neck/waist/hem/stocking landmarks. No pose is fitted independently.
 sy=np.floor(np.interp(np.arange(86)+.5,(0,8,30,44,56,60,86),(23,100,314,456,582,616,936))).astype(int)
 pal=np.array(PAL,np.int32);drawings=[]
 for n in range(4):
  start=int(n*cell);end=int((n+1)*cell)
  # Align the head's center, preserving the torso's shift relative to it.
  part=mask[:min(310,raw.shape[0]),start:end];py,px=np.where(part)
  center=(int(px.min())+int(px.max())+1)/2
  sx=np.floor(start+center+(np.arange(36)+.5-18)*scale).astype(int)
  a=np.zeros((86,36,4),np.uint8);valid=(sx>=start)&(sx<end)
  a[:,valid]=raw[sy[:,None],sx[None,valid]]
  a[a[:,:,3]<128]=0;a[a[:,:,3]>=128,3]=255
  delta=a[:,:,:3,None].astype(np.int32)-pal.T[None,None,:,:]
  index=(delta*delta).sum(2).argmin(2);a[:,:,:3]=pal[index].astype(np.uint8);a[a[:,:,3]==0]=0
  drawings.append(Image.fromarray(a))
 return drawings

DRAWINGS=import_drawings()
a=np.asarray(DRAWINGS[0]).copy();a[30:]=0;HEAD=Image.fromarray(a)

def layers_for(key,bob):
 a=np.asarray(key).copy();yy,xx=np.indices((86,36));rgb=a[:,:,:3].astype(int);alpha=a[:,:,3]>0
 cool=(rgb.min(2)>90)&(rgb.max(2)-rgb.min(2)<20)
 cloth=(yy>=43)&(yy<=57)&alpha&cool
 adjacent=np.zeros_like(cloth);adjacent[1:]|=cloth[:-1];adjacent[:-1]|=cloth[1:];adjacent[:,1:]|=cloth[:,:-1];adjacent[:,:-1]|=cloth[:,1:]
 hem=(yy>=53)&(yy<=57)&adjacent&(rgb[:,:,0]>150)&(rgb[:,:,0]-rgb[:,:,2]>15)
 skirt=cloth|hem|(adjacent&(rgb.max(2)<10))
 body=(yy>=30)&(yy<47)&~skirt
 leg=(yy>=30)&~skirt&~body
 masks=[leg&(xx>=18),leg&(xx<18),skirt,body]
 parts=[]
 for i,mask in enumerate(masks):
  b=a.copy();b[~mask]=0;parts.append(shift(Image.fromarray(b),bob if i>=2 else 0))
 parts.append(shift(HEAD,bob))
 return parts

# The pose drawings contain the contour and shading changes. Only a one-pixel
# down pose and a stable head drawing are composed on the native grid.
KEY_LAYERS=[layers_for(im,(0,1,0,0)[i]) for i,im in enumerate(DRAWINGS)]
WALK_LAYERS=list(KEY_LAYERS)
for layers in KEY_LAYERS:
 WALK_LAYERS.append([ImageOps.mirror(layers[1]),ImageOps.mirror(layers[0]),
                     ImageOps.mirror(layers[2]),ImageOps.mirror(layers[3]),layers[4].copy()])
KEYS=[flatten(layers) for layers in KEY_LAYERS]
WALK=[flatten(layers) for layers in WALK_LAYERS]
DURATION=120

def proof():
 b=Image.new('RGBA',(144,86),(105,99,112,255))
 for i,im in enumerate(KEYS):b.alpha_composite(im,(36*i,0))
 b.resize((1008,602),Image.Resampling.NEAREST).save(OUT/'Alisa_rear_four_keys.png')
 b=Image.new('RGBA',(288,86),(105,99,112,255))
 for i,im in enumerate(WALK):b.alpha_composite(im,(36*i,0))
 b.resize((1728,516),Image.Resampling.NEAREST).save(R/'review_final_cycle.png')
 print('Four drawn key poses, eight cels,36x86; direct source contours retained.')

if __name__=='__main__':proof()
