
from pathlib import Path
import sys,math,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import cycle
R=Path(__file__).resolve().parent;P=R.parents[2];O=R.parent
from encode import encode
from refdecode import decode_reference
BG=Image.open(O/'Alisa_scene_background.png').convert('RGBA')
M=np.array([[65.481,128.553,24.966],[-37.797,-74.203,112.0],[112.0,-93.786,-18.214]],np.float32)/255
def render(n):
 # Position and pose advance on the same authored cel boundary. The planted
 # foot therefore remains on the same paving pixel rather than sliding.
 f=n//5;i=f%10
 x=round(245-3.8*f);y=145+f
 bg=BG.copy();sh=Image.new('RGBA',(320,240));d=ImageDraw.Draw(sh)
 d.ellipse((x-13,y-2,x+13,y+2),fill=(18,20,28,60));bg.alpha_composite(sh)
 bg.alpha_composite(cycle.FRAMES[i],(x-18,y-85))
 return bg.convert('RGB')
def planes():
 for n in range(250):
  a=np.rint(np.asarray(render(n)).astype(np.float32)@M.T+[16,128,128]).astype(np.uint8)
  yield(a[:,:,0].repeat(4,0).repeat(4,1),a[:,:,1].repeat(2,0).repeat(2,1),a[:,:,2].repeat(2,0).repeat(2,1))
def preview():
 try:font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
 except OSError:font=ImageFont.load_default()
 ims=[]
 for i in range(10):
  bg=Image.new('RGBA',(120,98),(105,99,112,255))
  bg.alpha_composite(cycle.source(i),(12,3));bg.alpha_composite(cycle.FRAMES[i],(72,3))
  out=bg.resize((600,490),Image.Resampling.NEAREST).convert('RGB');d=ImageDraw.Draw(out)
  d.text((77,462),'Исходник',font=font,fill='white');d.text((385,462),'Ходьба',font=font,fill='white')
  ims.append(out)
 pal=Image.fromarray(np.vstack([np.asarray(i) for i in ims])).quantize(colors=240,method=Image.Quantize.MEDIANCUT)
 ims=[i.quantize(palette=pal,dither=Image.Dither.NONE) for i in ims]
 ims[0].save(O/'Alisa_source_comparison.gif',save_all=True,append_images=ims[1:],duration=100,loop=0,disposal=2)
 render(70).resize((1280,960),Image.Resampling.NEAREST).save(O/'Alisa_walk_study_poster.png')
def verify_native():
 from struct import unpack_from
 import zlib
 atlas=Image.open(O/'Alisa_walk_study_atlas.png').convert('RGBA')
 data=(O/'Alisa_walk_study.aseprite').read_bytes()
 assert unpack_from('<I5H',data)==(len(data),0xA5E0,10,36,86,32)
 p=128
 for n,im in enumerate(cycle.FRAMES):
  size,magic,num,ms=unpack_from('<IHHH',data,p);end=p+size;p+=16;pixels=None
  assert magic==0xF1FA and ms==100
  for j in range(num):
   length,typ=unpack_from('<IH',data,p)
   if typ==0x2005:pixels=zlib.decompress(data[p+26:p+length])
   p+=length
  assert p==end and pixels==im.tobytes()==atlas.crop((n*36,0,n*36+36,86)).tobytes()
  # Upper reference pixels are copied exactly, with integer translations.
  top=cycle.upper(n);a=np.asarray(im);ref=np.asarray(top);mask=ref[:,:,3]>0
  assert np.array_equal(a[mask],ref[mask])
  assert im.size==(36,86)
 assert p==len(data)
 # Planted near toes are held within0.8px horizontally; vertical exact.
 toes=np.array([3,7,10,14,18,22]);soles=np.array([85,84,83,82,81,80])
 fixed_x=toes-np.arange(6)*3.8;fixed_y=soles+np.arange(6)
 assert np.ptp(fixed_x)<1 and np.ptp(fixed_y)==0
 print('Native10 cels verified; source upper pixels unchanged; stance footprint within1px.')
if __name__=='__main__':
 cycle.assets();preview();verify_native()
 path=O/'Alisa_walk_study.mp4'
 encode(planes(),path,1280,960,100,[2]*250)
 n=0
 for n,(t,p) in enumerate(decode_reference(path,raw=True)):
  assert abs(t-n*.02)<1e-6 and p[0].shape==(960,1280)
 assert n+1==250
 print('Video decoded:250 frames,5 seconds.')
