
from pathlib import Path
from dataclasses import dataclass
from struct import pack,pack_into,unpack_from
import sys,json,zlib,bisect
import numpy as np
from PIL import Image,ImageDraw,ImageOps,ImageFont
R=Path(__file__).resolve().parent
P=R.parents[2]
OUT=R.parent;OUT.mkdir(exist_ok=True)
import cycle
import transitions as T
from encode import encode
from refdecode import decode_reference
BG=Image.open(OUT/'Alisa_scene_background.png').convert('RGBA')
SIZE=(36,86)
BASE=T.compose(T.IDLE_LOWER,4)
# A single edited breathing cel: original shirt rows lift one native pixel.
# Head, hands, skirt and legs retain their original pixels.
a=np.array(BASE);high=a.copy();high[32:42,6:27]=a[33:43,6:27]
BREATH=Image.fromarray(high)
IDLE=[BASE,BASE,BREATH,BREATH,BREATH,BASE,BASE,BASE]
IDLE_MS=[500,200,200,500,200,200,200,400]
START=[T.compose(im,phase) for im,phase in zip(T.START_LOWER,T.START_UPPER_PHASES)]
STOP=[T.compose(im,phase) for im,phase in zip(T.STOP_LOWER,T.STOP_UPPER_PHASES)]
LEFT=list(cycle.FRAMES)
RIGHT=[ImageOps.mirror(im) for im in LEFT]
TURN=[]
for phase,mirror in ((4,False),(5,False),(6,False),(6,True),(5,True),(4,True)):
 im=Image.new('RGBA',SIZE)
 im.paste(cycle.source(phase),(cycle.NECK_DX[phase],0))
 TURN.append(ImageOps.mirror(im) if mirror else im)
DANCE=[cycle.source((i+5)%40) for i in range(40)]
CLIPS=[
 ('idle_left',IDLE,IDLE_MS,0),
 ('start_left',START,[100]*5,0),
 ('walk_left',LEFT,[100]*10,0),
 ('stop_left',STOP,[100]*5,0),
 ('turn_left_right',TURN,[100]*6,0),
 ('idle_right',[ImageOps.mirror(im) for im in IDLE],IDLE_MS,0),
 ('start_right',[ImageOps.mirror(im) for im in START],[100]*5,0),
 ('walk_right',RIGHT,[100]*10,0),
 ('stop_right',[ImageOps.mirror(im) for im in STOP],[100]*5,0),
 ('dance_original',DANCE,[100]*40,3)
]
BANK={name:(ims,ms,offset) for name,ims,ms,offset in CLIPS}

def chunk(k,b):return pack('<IH',len(b)+6,k)+b

def export():
 total=sum(len(ims) for _,ims,_,_ in CLIPS);sheet=Image.new('RGBA',(360,86*((total+9)//10)))
 entries=[];tags=[];flat=[];i=0
 for name,ims,durations,offset in CLIPS:
  once=name.startswith(('start','stop','turn'))
  tags.append({'name':name,'from':i,'to':i+len(ims)-1,'direction':'forward','repeat':1 if once else 0,'loop':not once,'drawOffset':{'x':offset,'y':0},'pivot':{'x':18-offset,'y':85}})
  for n,(im,ms) in enumerate(zip(ims,durations)):
   x=i%10*36;y=i//10*86;sheet.paste(im,(x,y))
   entries.append({'filename':f'{name}_{n:02}.png','frame':{'x':x,'y':y,'w':36,'h':86},'duration':ms,'trimmed':False,'rotated':False,'sourceSize':{'w':36,'h':86},'spriteSourceSize':{'x':0,'y':0,'w':36,'h':86}})
   flat.append((im,ms));i+=1
 sheet.save(OUT/'Alisa_motion_next_atlas.png',optimize=True)
 meta={'image':'Alisa_motion_next_atlas.png','format':'RGBA8888','size':{'w':sheet.width,'h':sheet.height},'scale':'1','frameTags':tags}
 (OUT/'Alisa_motion_next.json').write_text(json.dumps({'frames':entries,'meta':meta},ensure_ascii=False,indent=2),encoding='utf-8')
 data=pack('<H8x',len(tags))
 for tag in tags:
  s=tag['name'].encode();data+=pack('<HHBH6x3BBH',tag['from'],tag['to'],0,tag['repeat'],128,188,220,0,len(s))+s
 tagchunk=chunk(0x2018,data)
 frames=[]
 for n,(im,ms) in enumerate(flat):
  cs=[]
  if n==0:
   name='Алиса'.encode('utf-8');cs.append(chunk(0x2004,pack('<6HB3xH',3,0,0,0,0,0,255,len(name))+name));cs.append(tagchunk)
  cs.append(chunk(0x2005,pack('<HhhBHh5xHH',0,0,0,255,2,0,36,86)+zlib.compress(im.tobytes(),9)))
  raw=b''.join(cs);frames.append(pack('<IHHH2xI',len(raw)+16,0xF1FA,len(cs),ms,0)+raw)
 raw=b''.join(frames);header=bytearray(128);pack_into('<IHHHHHIH',header,0,len(raw)+128,0xA5E0,total,36,86,32,1,100);header[34:36]=bytes((1,1))
 doc=header+raw;(OUT/'Alisa_motion_next.aseprite').write_bytes(doc)
 # Read every cel back, independently of the atlas layout.
 pos=128
 for n,(im,ms) in enumerate(flat):
  size,magic,num,duration=unpack_from('<IHHH',doc,pos);end=pos+size;pos+=16;pixels=None
  assert magic==0xF1FA and duration==ms
  for _ in range(num):
   length,kind=unpack_from('<IH',doc,pos)
   if kind==0x2005:pixels=zlib.decompress(doc[pos+26:pos+length])
   pos+=length
  assert pos==end and pixels==im.tobytes()
  assert sheet.crop((n%10*36,n//10*86,n%10*36+36,n//10*86+86)).tobytes()==pixels
 assert pos==len(doc)
 print('Native export:',total,'frames;',len(tags),'tags; atlas/Aseprite pixel match.',flush=True)

@dataclass
class Cel:
 start:int
 duration:int
 image:object
 x:float
 y:float
 offset:int
 label:str

CELS=[];clock=0
def add(im,ms,x,y,label,offset=0):
 global clock
 assert ms%20==0
 CELS.append(Cel(clock,ms,im,x,y,offset,label));clock+=ms
def clip(name,x,y,repeat=1):
 ims,ms,offset=BANK[name]
 for _ in range(repeat):
  for im,d in zip(ims,ms):add(im,d,x,y,name,offset)

x,y=238.,142.
clip('idle_left',x,y)
clip('start_left',x,y)
for n in range(1,21):
 x-=3.8;y+=1;add(LEFT[n%10],100,x,y,'walk_left')
for im in STOP[1:]:add(im,100,x,y,'stop_left')
add(BASE,800,x,y,'idle_left')
DANCE_START=clock
clip('dance_original',x,y,2)
DANCE_END=clock
add(BASE,800,x,y,'idle_left')
clip('turn_left_right',x,y)
add(BANK['idle_right'][0][0],400,x,y,'idle_right')
clip('start_right',x,y)
for n in range(1,21):
 x+=3.8;y+=1;add(RIGHT[n%10],100,x,y,'walk_right')
for im in BANK['stop_right'][0][1:]:add(im,100,x,y,'stop_right')
clip('idle_right',x,y)
TOTAL=clock;STARTS=[c.start for c in CELS]

def actor(im,offset=0):
 canvas=Image.new('RGBA',(48,86));canvas.alpha_composite(im,(6+offset,0));return canvas

def validate():
 T.validate()
 assert BASE.tobytes()==START[0].tobytes()==STOP[-1].tobytes()
 assert LEFT[0].tobytes()==START[-1].tobytes()==STOP[0].tobytes()
 assert TURN[0].tobytes()==BASE.tobytes()
 assert TURN[-1].tobytes()==BANK['idle_right'][0][0].tobytes()
 assert actor(DANCE[-1],3).tobytes()==actor(BASE).tobytes()
 assert np.array_equal(np.array(BREATH)[:32],np.array(BASE)[:32])
 assert np.array_equal(np.array(BREATH)[43:],np.array(BASE)[43:])
 # Protect the already-approved walk from unintentional edits.
 approved=Image.open(P/'alisa/walk_redo/Alisa_walk_study_atlas.png').convert('RGBA')
 for n,im in enumerate(LEFT):assert im.tobytes()==approved.crop((n*36,0,n*36+36,86)).tobytes()
 for n,im in enumerate(RIGHT):assert im.tobytes()==ImageOps.mirror(LEFT[n]).tobytes()
 for n,im in enumerate(DANCE):assert im.tobytes()==cycle.source((n+5)%40).tobytes()
 for cel in CELS:
  bbox=cel.image.getbbox();l=round(cel.x)-18+cel.offset;t=round(cel.y)-85
  assert bbox and l+bbox[0]>=0 and t+bbox[1]>=0 and l+bbox[2]<=320 and t+bbox[3]<=240
 print('Approved walk preserved. Start/stop endpoints exact. Original dance pixels preserved; full sprites fit stage.',flush=True)

def at(ms):
 c=CELS[min(len(CELS)-1,bisect.bisect_right(STARTS,ms)-1)]
 return c
def render(ms):
 c=at(ms);x,y=round(c.x),round(c.y)
 out=BG.copy();sh=Image.new('RGBA',(320,240));d=ImageDraw.Draw(sh)
 d.ellipse((x-14,y-2,x+14,y+2),fill=(18,20,28,60));out.alpha_composite(sh)
 out.alpha_composite(c.image,(x-18+c.offset,y-85))
 return out.convert('RGB')
M=np.array([[65.481,128.553,24.966],[-37.797,-74.203,112.0],[112.0,-93.786,-18.214]],np.float32)/255
def yuv(im):
 a=np.rint(np.asarray(im).astype(np.float32)@M.T+[16,128,128]).astype(np.uint8)
 return (a[:,:,0].repeat(4,0).repeat(4,1),a[:,:,1].repeat(2,0).repeat(2,1),a[:,:,2].repeat(2,0).repeat(2,1))
def planes():
 for t in range(0,TOTAL,20):yield yuv(render(t))

def previews():
 # A full start -> step -> stop sequence at native cadence, without position shifts.
 ims=[(BASE,500)]+list(zip(START,[100]*5))+list(zip(LEFT[1:]+LEFT[:1],[100]*10))+list(zip(STOP[1:],[100]*4))+[(BASE,600)]
 scaled=[]
 for im,ms in ims:
  bg=Image.new('RGBA',(60,96),(105,99,112,255));bg.alpha_composite(im,(12,4))
  scaled.append(bg.resize((360,576),Image.Resampling.NEAREST).convert('RGB'))
 sample=Image.fromarray(np.vstack([np.asarray(i) for i in scaled]));pal=sample.quantize(colors=240,method=Image.Quantize.MEDIANCUT)
 q=[im.quantize(palette=pal,dither=Image.Dither.NONE) for im in scaled]
 q[0].save(OUT/'Alisa_start_stop.gif',save_all=True,append_images=q[1:],duration=[ms for _,ms in ims],loop=0,disposal=2)
 render(DANCE_START+700).resize((1280,960),Image.Resampling.NEAREST).save(OUT/'Alisa_motion_next_poster.png')
 timeline={'durationMs':TOTAL,'fps':50,'danceStartMs':DANCE_START,'danceEndMs':DANCE_END,
           'spriteSize':[36,86],'celCount':len(CELS),'timeline':[{'startMs':c.start,'durationMs':c.duration,'clip':c.label,'position':[c.x,c.y],'drawOffsetX':c.offset} for c in CELS]}
 (OUT/'Alisa_motion_next_timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
 # Inspect entry/exit and native pose changes on one contact sheet.
 times=[0,2600,3800,5000,DANCE_START+700,DANCE_END, DANCE_END+1000,TOTAL-500]
 board=Image.new('RGB',(1280,520),(40,42,50));d=ImageDraw.Draw(board)
 for n,t in enumerate(times):
  t=min(t,TOTAL-20);xx=n%4*320;yy=n//4*260;board.paste(render(t),(xx,yy));d.text((xx+5,yy+243),f'{t/1000:.2f}s {at(t).label}',fill='white')
 board.save(R/'scene_review.png')
 print('Scene',TOTAL/1000,'s. Original dance',DANCE_START/1000,'to',DANCE_END/1000,flush=True)

def verify_video(path):
 count=0;err=0
 for n,(t,actual) in enumerate(decode_reference(path,raw=True)):
  assert abs(t-n*.02)<1e-6 and actual[0].shape==(960,1280)
  if n%25==0:
   for a,b in zip(yuv(render(n*20)),actual):err=max(err,int(np.abs(a.astype(np.int16)-b.astype(np.int16)).max()))
  count+=1
 assert count==TOTAL//20 and err<=6,(count,TOTAL//20,err)
 print('Video verified:',count,'frames;',TOTAL/1000,'s; max sampled YUVerror',err,flush=True)

if __name__=='__main__':
 export();validate();previews()
 if '--render' in sys.argv:
  path=OUT/'Alisa_motion_next.mp4';encode(planes(),path,1280,960,100,[2]*(TOTAL//20));verify_video(path)


 if '--verify-video' in sys.argv and '--render' not in sys.argv:verify_video(OUT/'Alisa_motion_next.mp4')
