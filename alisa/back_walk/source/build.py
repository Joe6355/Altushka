"""Layered Aseprite export and continuous scene for the new rear directions."""
from pathlib import Path
from dataclasses import dataclass
from struct import pack,pack_into,unpack_from
import json,zlib,sys,bisect
import numpy as np
from PIL import Image,ImageDraw,ImageOps
import rear as C

R=Path(__file__).resolve().parent
P=R.parents[2]
OUT=R.parent
SIZE=(36,86)
CLIPS=C.CLIPS
LAYER_NAMES=('задняя нога','таз','передняя нога','юбка','кофта','голова')
BG=Image.open(OUT/'Alisa_scene_background.png').convert('RGBA')

def shadow_offset(name,index):
 amount=5 if name.endswith('_back') else 3
 if name.startswith('idle'):return 0
 if name.startswith('walk'):return -amount
 progress=index/4 if name.startswith('start') else 1-index/4
 return -round(amount*progress)

def chunk(kind,data):return pack('<IH',len(data)+6,kind)+data

def export():
 total=sum(len(cels) for _,cels,_,_,_ in CLIPS)
 atlas=Image.new('RGBA',(360,86*((total+9)//10)))
 flat=[];entries=[];tags=[];n=0
 for name,cels,durations,pivot,velocity in CLIPS:
  once=name.startswith(('start','stop'))
  tags.append({'name':name,'from':n,'to':n+len(cels)-1,'direction':'forward','repeat':1 if once else 0,'loop':not once,'pivot':{'x':pivot,'y':85},'velocityPxPerSecond':{'x':velocity[0],'y':velocity[1]}})
  for i,(layers,ms) in enumerate(zip(cels,durations)):
   im=C.flatten(layers);x=n%10*36;y=n//10*86;atlas.paste(im,(x,y))
   entries.append({'filename':f'{name}_{i:02}.png','frame':{'x':x,'y':y,'w':36,'h':86},'duration':ms,'trimmed':False,'rotated':False,'sourceSize':{'w':36,'h':86},'spriteSourceSize':{'x':0,'y':0,'w':36,'h':86},'shadowOffsetY':shadow_offset(name,i)})
   flat.append((layers,im,ms));n+=1
 atlas.save(OUT/'Alisa_back_atlas.png',optimize=True)
 meta={'image':'Alisa_back_atlas.png','format':'RGBA8888','size':{'w':atlas.width,'h':atlas.height},'scale':'1','frameTags':tags,'layers':[{'name':name,'opacity':255,'blendMode':'normal'} for name in LAYER_NAMES]}
 (OUT/'Alisa_back.json').write_text(json.dumps({'frames':entries,'meta':meta},ensure_ascii=False,indent=2),encoding='utf-8')
 tagdata=pack('<H8x',len(tags))
 for tag in tags:
  name=tag['name'].encode('utf-8')
  tagdata+=pack('<HHBH6x3BBH',tag['from'],tag['to'],0,tag['repeat'],128,188,220,0,len(name))+name
 frames=[]
 for n,(layers,im,ms) in enumerate(flat):
  chunks=[]
  if n==0:
   for name in LAYER_NAMES:
    s=name.encode('utf-8');chunks.append(chunk(0x2004,pack('<6HB3xH',3,0,0,0,0,0,255,len(s))+s))
   chunks.append(chunk(0x2018,tagdata))
  for i,layer in enumerate(layers):
   chunks.append(chunk(0x2005,pack('<HhhBHh5xHH',i,0,0,255,2,0,36,86)+zlib.compress(layer.tobytes(),9)))
  data=b''.join(chunks);frames.append(pack('<IHHH2xI',len(data)+16,0xF1FA,len(chunks),ms,0)+data)
 data=b''.join(frames);header=bytearray(128)
 pack_into('<IHHHHHIH',header,0,len(data)+128,0xA5E0,total,36,86,32,1,100);header[34:36]=bytes((1,1))
 doc=header+data;(OUT/'Alisa_back.aseprite').write_bytes(doc)
 pos=128
 for n,(layers,im,ms) in enumerate(flat):
  length,magic,num,duration=unpack_from('<IHHH',doc,pos);end=pos+length;pos+=16;readlayers={}
  assert magic==0xF1FA and duration==ms
  for _ in range(num):
   size,kind=unpack_from('<IH',doc,pos)
   if kind==0x2005:
    index=unpack_from('<H',doc,pos+6)[0]
    readlayers[index]=Image.frombytes('RGBA',SIZE,zlib.decompress(doc[pos+26:pos+size]))
   pos+=size
  assert pos==end and len(readlayers)==6
  decoded=C.flatten([readlayers[i] for i in range(6)])
  assert decoded.tobytes()==im.tobytes()==atlas.crop((n%10*36,n//10*86,n%10*36+36,n//10*86+86)).tobytes()
 assert pos==len(doc)
 print('Export verified:',total,'frames,',len(tags),'tags, six layers;',atlas.size,flush=True)

def validate():
 for model in (C.BACK,C.DIAGONAL):
  assert C.flatten(model.start_layers[0]).tobytes()==C.flatten(model.idle_layers[0]).tobytes()
  assert C.flatten(model.start_layers[-1]).tobytes()==C.flatten(model.walk_layers[0]).tobytes()
  assert C.flatten(model.stop_layers[-1]).tobytes()==C.flatten(model.idle_layers[0]).tobytes()
  for i,layers in enumerate(model.walk_layers):
   head=np.asarray(layers[-1]);ref=np.asarray(C.shift(model.head,C.SWAY[i],C.BOB[i]))
   assert np.array_equal(head[10:],ref[10:])
   assert not ((head[:,:,0]<80)&(head[:,:,1]>120)&(head[:,:,2]>170)&(head[:,:,3]>0)).any()
 for _,cels,_,_,_ in CLIPS:
  for layers in cels:
   im=C.flatten(layers);a=np.asarray(im)
   assert im.size==SIZE and set(np.unique(a[:,:,3]))<={0,255}
 # Check native leg bounds before clipping, and pinning of the stance heels.
 for points in C.N_LEG:
  for x,y in points:assert 0<=x<36 and 0<=y<86
 for points in C.NE_LEG:
  for x,y in points:assert 0<=x<36 and 0<=y<86 and 0<=x-6<36 and 0<=y-1<86
 n_ground=[];ne_ground=[]
 for i in range(6):
  heel=C.N_HEEL[i];assert C.n_leg(i).getpixel((12,heel))[3]==255
  n_ground.append(heel-2*i)
  x=(34,30,26,23,19,15)[i];y=77+i
  assert C.ne_leg(i).getpixel((x,y))[3]==255
  ne_ground.append((round(120+3.8*i)+x,y-i))
 assert len(set(n_ground))==1 and len(set(ne_ground))==1
 for i,layers in enumerate(C.DIAGONAL.walk_layers):assert C.flatten(C.mirrored(layers)).tobytes()==ImageOps.mirror(C.flatten(layers)).tobytes()
 print('Native36x86; no clipping; start/stop endpoints exact; rear feet planted; no rear-facing eyes.',flush=True)

BANK={name:(layers,durations,pivot,velocity) for name,layers,durations,pivot,velocity in CLIPS}
@dataclass
class Cel:
 start:int
 duration:int
 image:object
 x:float
 y:float
 pivot:int
 shadow:int
 label:str

CELS=[];clock=0
def add(name,index,duration,x,y):
 global clock
 layers,ms,pivot,velocity=BANK[name]
 assert duration%20==0
 CELS.append(Cel(clock,duration,C.flatten(layers[index]),x,y,pivot,shadow_offset(name,index),name));clock+=duration

def sequence(name,x,y,skip=0):
 layers,ms,_,_=BANK[name]
 for i in range(skip,len(layers)):add(name,i,ms[i],x,y)

x,y=120.,212.
for i,ms in ((0,600),(1,300),(2,300)):add('idle_back',i,ms,x,y)
sequence('start_back',x,y)
for n in range(1,21):
 y-=2;add('walk_back',n%10,100,x,y)
sequence('stop_back',x,y,1);add('idle_back',0,400,x,y)
add('idle_back_right',0,200,x,y);sequence('start_back_right',x,y)
for n in range(1,21):
 x+=3.8;y-=1;add('walk_back_right',n%10,100,x,y)
sequence('stop_back_right',x,y,1);add('idle_back_right',0,400,x,y)
# Turn through the intermediate rear stance at rest; no crossfades or morphs.
add('idle_back',0,200,x,y);add('idle_back_left',0,200,x,y)
sequence('start_back_left',x,y)
for n in range(1,21):
 x-=3.8;y-=1;add('walk_back_left',n%10,100,x,y)
sequence('stop_back_left',x,y,1);sequence('idle_back_left',x,y)
TOTAL=clock;STARTS=[c.start for c in CELS]

def at(ms):return CELS[min(len(CELS)-1,bisect.bisect_right(STARTS,ms)-1)]
def render(ms):
 c=at(ms);x,y=round(c.x),round(c.y);out=BG.copy();shadow=Image.new('RGBA',BG.size)
 ImageDraw.Draw(shadow).ellipse((x-12,y+c.shadow-2,x+12,y+c.shadow+2),fill=(18,20,28,60));out.alpha_composite(shadow)
 out.alpha_composite(c.image,(x-c.pivot,y-85))
 return out.convert('RGB')

def gif(images,durations,path):
 rgb=[im.convert('RGB') for im in images]
 palette=Image.fromarray(np.vstack([np.asarray(im) for im in rgb])).quantize(colors=240,method=Image.Quantize.MEDIANCUT)
 q=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in rgb]
 q[0].save(path,save_all=True,append_images=q[1:],duration=durations,loop=0,disposal=2)

def triptych(images):
 bg=Image.new('RGBA',(144,98),(105,99,112,255))
 for n,im in enumerate(images):bg.alpha_composite(im,(n*48+6,6))
 return bg.resize((864,588),Image.Resampling.NEAREST).convert('RGB')

def previews():
 gif([triptych((C.flatten(C.DIAGONAL.walk_layers[i]),C.flatten(C.BACK.walk_layers[i]),C.flatten(C.mirrored(C.DIAGONAL.walk_layers[i])))) for i in range(10)],[100]*10,OUT/'Alisa_back_walk.gif')
 gif([triptych((C.flatten(C.DIAGONAL.idle_layers[i]),C.flatten(C.BACK.idle_layers[i]),C.flatten(C.mirrored(C.DIAGONAL.idle_layers[i])))) for i in range(4)],C.IDLE_MS,OUT/'Alisa_back_idle.gif')
 # Full start -> two steps -> closing step for all three new directions.
 ids=[('idle',0,500)]+[('start',i,100) for i in range(5)]+[('walk',i%10,100) for i in range(1,11)]+[('stop',i,100) for i in range(1,5)]+[('idle',0,600)]
 ims=[]
 for state,i,ms in ids:
  ims.append(triptych([C.flatten(BANK[f'{state}_{name}'][0][i]) for name in ('back_right','back','back_left')]))
 gif(ims,[ms for _,_,ms in ids],OUT/'Alisa_back_transitions.gif')
 side=Image.open(P/'alisa/side_walk/Alisa_side_idle.png').convert('RGBA')
 bg=Image.new('RGBA',(144,96),(105,99,112,255))
 for n,im in enumerate((side,C.flatten(C.DIAGONAL.idle_layers[0]),C.flatten(C.BACK.idle_layers[0]),C.flatten(C.mirrored(C.DIAGONAL.idle_layers[0])))):bg.alpha_composite(im,(n*36,5))
 bg.resize((1152,768),Image.Resampling.NEAREST).save(OUT/'Alisa_back_model.png')
 render(2800).resize((1280,960),Image.Resampling.NEAREST).save(OUT/'Alisa_back_scene_poster.png')
 timeline={'durationMs':TOTAL,'fps':50,'spriteSize':[36,86],'timeline':[{'startMs':c.start,'durationMs':c.duration,'clip':c.label,'position':[c.x,c.y],'pivotX':c.pivot,'shadowOffsetY':c.shadow} for c in CELS]}
 (OUT/'Alisa_back_timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
 board=Image.new('RGB',(1280,520),(40,42,50));d=ImageDraw.Draw(board)
 for i,t in enumerate((0,1600,2800,4200,5500,7600,9400,TOTAL-500)):
  xx=i%4*320;yy=i//4*260;board.paste(render(t),(xx,yy));d.text((xx+6,yy+243),f'{t/1000:.2f}s {at(t).label}',fill='white')
 board.save(R/'scene_review.png')
 print('Continuous scene',TOTAL/1000,'s;',TOTAL//20,'video frames.',flush=True)

M=np.array([[65.481,128.553,24.966],[-37.797,-74.203,112.0],[112.0,-93.786,-18.214]],np.float32)/255
def yuv(im):
 a=np.rint(np.asarray(im).astype(np.float32)@M.T+[16,128,128]).astype(np.uint8)
 return (a[:,:,0].repeat(4,0).repeat(4,1),a[:,:,1].repeat(2,0).repeat(2,1),a[:,:,2].repeat(2,0).repeat(2,1))
def planes():
 for t in range(0,TOTAL,20):yield yuv(render(t))
def verify_video():
 from refdecode import decode_reference
 count=0;err=0
 for n,(t,actual) in enumerate(decode_reference(OUT/'Alisa_back_scene.mp4',raw=True)):
  assert abs(t-n*.02)<1e-6 and actual[0].shape==(960,1280)
  if n%25==0:
   for a,b in zip(yuv(render(n*20)),actual):err=max(err,int(np.abs(a.astype(np.int16)-b.astype(np.int16)).max()))
  count+=1
 assert count==TOTAL//20 and err<=6,(count,err)
 print('Video verified:',count,'frames;',TOTAL/1000,'s; sampled max YUVerror',err,flush=True)

if __name__=='__main__':
 export();validate();previews()
 if '--render' in sys.argv:
  from encode import encode
  encode(planes(),OUT/'Alisa_back_scene.mp4',1280,960,50);verify_video()
 elif '--verify-video' in sys.argv:verify_video()
