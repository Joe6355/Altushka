
from pathlib import Path
import math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import core
from pipeline import state,INTRO,WALK_END,TOTAL
R=Path(__file__).resolve().parent;O=R.parent
try:f=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
except OSError:f=ImageFont.load_default()
frames=[]
for n in range(32):
 phase=n/16*math.tau;t=n*.06
 native=Image.new('RGBA',(144,96),(100,94,108,255))
 for i,(v,a,d) in enumerate((('down',1,0),('down_left',1,0),('down_left',0,1))):
  native.alpha_composite(core.character(v,phase,a,d,t),(i*48+6,2))
 im=native.resize((720,480),Image.Resampling.NEAREST).convert('RGB');dr=ImageDraw.Draw(im)
 for i,label in enumerate(('Вперёд','Диагональ','Танец')):dr.text((i*240+55,453),label,font=f,fill=(235,230,240))
 frames.append(im)
sample=Image.fromarray(np.vstack([np.asarray(i) for i in frames[::4]]))
pal=sample.quantize(colors=240,method=Image.Quantize.MEDIANCUT)
q=[i.quantize(palette=pal,dither=Image.Dither.NONE) for i in frames]
q[0].save(O/'Alisa_motion_detail.gif',save_all=True,append_images=q[1:],duration=60,loop=0,disposal=2)
# Faces remain the original approved pixels; only the hair tips move.
reference=core.parts('down')[0].crop((8,17,24,26)).tobytes()
for i in range(32):
 im=core.character('down',i/32*math.tau,1,0,i/32)
 assert im.crop((8,17,24,26)).tobytes()==reference
for v in core.VIEWS:
 a=core.character(v,0,1,0,0)
 b=core.character(v,math.tau,1,0,.96)
 assert a.tobytes()==b.tobytes(),v
assert core.character('down_left',0,0,1,0).tobytes()==core.character('down_left',math.tau*4,0,1,4).tobytes()
counts={v:0 for v in core.VIEWS};previous=None
for t in range(0,TOTAL,20):
 view=state(t)[1];index=core.VIEWS.index(view)
 if previous is not None:
  delta=(index-previous+4)%8-4
  assert abs(delta)<=1,(t,previous,index)
 previous=index
 if INTRO*1000<=t<WALK_END*1000:counts[view]+=.02
print('Face pixels invariant; walk and dance loops close exactly; no skipped turn headings.')
print('Visible walk headings seconds:',{k:round(v,2) for k,v in counts.items()})
