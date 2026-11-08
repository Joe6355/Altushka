
from pathlib import Path
from functools import lru_cache
import math
import numpy as np
from PIL import Image,ImageDraw,ImageOps
import original
R=Path(__file__).parent
SIZE=(36,86)
VIEWS=('down','down_left','left','up_left','up','up_right','right','down_right')
PAL=np.array([(0,0,0),(13,13,18),(24,24,29),(36,36,42),(55,55,61),(154,154,161),(210,210,215),(242,242,245),(253,253,254),(212,214,223),(241,242,246),(255,255,255),(169,79,106),(215,124,128),(247,186,188),(255,242,231),(22,29,54),(61,95,139),(65,157,231),(114,239,232)],int)

def quant(im):
 a=np.array(im);m=a[:,:,3]>0;rgb=a[m,:3].astype(int)
 a[m,:3]=PAL[((rgb[:,None]-PAL[None])**2).sum(2).argmin(1)]
 return Image.fromarray(a)
def move(im,dx=0,dy=0):
 out=Image.new('RGBA',SIZE);out.paste(im,(int(round(dx)),int(round(dy))));return out
def masked(im,polygon):
 a=np.array(im);m=Image.new('1',SIZE);ImageDraw.Draw(m).polygon(polygon,fill=1)
 a[~np.asarray(m)]=0;return Image.fromarray(a)

@lru_cache(None)
def parts(view):
 mirror=view in ('right','up_right','down_right')
 key={'right':'left','up_right':'up_left','down_right':'down_left'}.get(view,view)
 if key in ('down','down_left'):
  h=original.HEADS['still'].copy();t=original.TORSO.copy()
  cloth=original.stamp(*((original.SKIRTS['still'][0],original.PIVOT,original.SKIRTS['still'][1])))
 else:
  i={'left':0,'up_left':1,'up':2}[key]
  im=quant(Image.open(R/f'turn_{i}.png').convert('RGBA'))
  h=np.array(im);h[31:]=0;h=Image.fromarray(h)
  # Match the original head width, keeping the neck anchor on the same grid.
  bbox=h.getbbox();factor=28/(bbox[2]-bbox[0])
  h=h.transform(SIZE,Image.Transform.AFFINE,(1/factor,0,17.5-17.5/factor,0,1,0),Image.Resampling.NEAREST)
  if key=='left':poly=[(16,29),(22,29),(23,32),(23,39),(21,44),(13,44),(10,41),(9,35),(12,32)]
  else:poly=[(12,29),(23,29),(24,33),(23,40),(22,44),(12,44),(11,39),(11,32)]
  t=masked(im,poly)
  aa=np.array(t);rgb=aa[:,:,:3].astype(int);skin=(rgb[:,:,0]>130)&(rgb[:,:,0]-rgb[:,:,2]>15)
  if key!='left':aa[skin]=0
  t=Image.fromarray(aa)
  p=np.array(im);yy,xx=np.indices((86,36));rgb=p[:,:,:3].astype(int)
  fabric=(p[:,:,3]>0)&(yy>=42)&(yy<=59)&(rgb.min(2)>135)&(rgb[:,:,2]>=rgb[:,:,0]-5)&(rgb.max(2)-rgb.min(2)<36)
  p[~fabric]=0;cloth=Image.fromarray(p)
 if mirror:h,t,cloth=map(ImageOps.mirror,(h,t,cloth))
 return h,t,cloth

@lru_cache(None)
def source_skirt(index):
 im=original.sprite(index%10);p=np.array(im);rgb=p[:,:,:3].astype(int);yy,xx=np.indices((86,36))
 m=(p[:,:,3]>0)&(yy>=41)&(yy<=60)&(rgb.min(2)>150)&(rgb[:,:,2]>=rgb[:,:,0]-5)&(rgb.max(2)-rgb.min(2)<36)
 counts=m.sum(1);rows=np.flatnonzero((counts>=4)&(np.arange(86)>=41))
 wy=int(rows.min());wx=float(np.median(np.where(m[wy:wy+2])[1]))
 p[~m]=0
 return original.stamp(Image.fromarray(p),(17.5,43),(wx,wy))

def torso(view,phase,amount,bob,dance,sway,time):
 base=np.array(parts(view)[1]);yy,xx=np.indices((86,36))
 rear=view.startswith('up')
 mass=(.32 if rear else 1.30)*amount*math.sin(2*phase-1.15)+(.38 if rear else .6)*(1-amount)*(1-dance)*math.sin(time*math.tau/2.88-.5)
 mass+=dance*(.45 if rear else .85)*math.sin(2*phase-1.1)
 envelope=np.exp(-((yy-37)/3.3)**2)
 sy=np.rint(yy-bob-mass*envelope).astype(int)
 width=1+(0.015 if rear else .035)*amount*math.sin(2*phase-.7)*envelope
 sx=np.rint(17.5+(xx-17.5-sway*.8)/width).astype(int)
 valid=(sy>=0)&(sy<86)&(sx>=0)&(sx<36)
 out=np.zeros_like(base);out[valid]=base[sy[valid],sx[valid]]
 return Image.fromarray(out)

def skirt(view,phase,amount,bob,dance,sway,time):
 dynamic=max(amount,dance)
 if view in ('down','down_left','down_right'):
  index=int(((phase-.7)/(2*math.pi)%1)*10) if dynamic>.15 else 4
  base=source_skirt(index)
  if view=='down_right':base=ImageOps.mirror(base)
 else:base=parts(view)[2]
 a=np.asarray(base);yy,xx=np.indices((86,36));f=np.clip((yy-43)/14,0,1)
 # Waist stays attached; pleats and hem have a delayed, asymmetric follow-through.
 side=1.6*dynamic*math.sin(phase-.85)+.3*(1-dynamic)*math.sin(time*math.tau/2.88)
 width=1+.09*dynamic*math.sin(2*phase-1.05)*f
 sx=np.rint(17.5+(xx-17.5-sway-side*f)/width).astype(int)
 flutter=1.3*dynamic*np.sin(2*phase-.6+(xx-18)*.18)*f*f
 sy=np.rint(yy-bob-flutter).astype(int)
 valid=(sx>=0)&(sx<36)&(sy>=0)&(sy<86)
 out=np.zeros_like(a);out[valid]=a[sy[valid],sx[valid]]
 return Image.fromarray(out)

def head(view,phase,amount,bob,dance,sway,time):
 a=np.array(parts(view)[0]);rgb=a[:,:,:3].astype(int);yy,xx=np.indices((86,36))
 hair=(a[:,:,3]>0)&(rgb.min(2)>130)&(rgb.max(2)-rgb.min(2)<42)&(rgb[:,:,2]>=rgb[:,:,0]-4)
 tips=hair&(yy>=26);tuft=hair&(yy<=8)
 dx=int(round(max(amount,dance)*math.sin(phase-1.15)))
 out=a.copy()
 for mask,shift in ((tips,dx),(tuft,-dx)):
  out[mask]=0
  ys,xs=np.where(mask);dest=xs+shift;ok=(dest>=0)&(dest<36)
  out[ys[ok],dest[ok]]=a[ys[ok],xs[ok]]
 return move(Image.fromarray(out),sway*.35,bob*.65)

def character(view,phase,amount=1.,dance=0.,time=0.):
 import limbs
 phase=round(phase%math.tau,10)
 bob=.72*amount*math.sin(2*phase-.3)+.25*(1-amount)*(1-dance)*math.sin(time*math.tau/2.88)+.65*dance*math.sin(2*phase)
 sway=dance*2.6*math.sin(phase)
 fx,fy=limbs.VECTORS[view]
 limb_phase=phase+(math.pi if (fy>=0 and fx<0) or (fy<0 and fx>=0) else 0)
 far,near=limbs.arms(view,limb_phase,amount,bob,dance=dance,sway=sway)
 layers=[limbs.legs(view,limb_phase,amount,bob,dance=dance,sway=sway),far,torso(view,phase,amount,bob,dance,sway,time),
         skirt(view,phase,amount,bob,dance,sway,time),head(view,phase,amount,bob,dance,sway,time),near]
 forearm=np.array(far);forearm[:37]=0
 layers=[layers[0],far,layers[2],layers[3],Image.fromarray(forearm),layers[4],near]
 out=Image.new('RGBA',SIZE)
 for im in layers:out.alpha_composite(im)
 return out

if __name__=='__main__':
 for mode in ('walk','dance'):
  bg=Image.new('RGBA',(36*16,86*8),(105,99,111,255))
  for row,v in enumerate(VIEWS):
   for i in range(16):
    im=character(v,i/16*math.tau,1 if mode=='walk' else 0,1 if mode=='dance' else 0,i/16)
    bg.alpha_composite(im,(i*36,row*86))
  bg.resize((1728,2064),Image.Resampling.NEAREST).convert('RGB').save(R/(mode+'_qa.png'))
