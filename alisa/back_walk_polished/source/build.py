"""Export and verify the polished rear-direction animation package."""
from pathlib import Path
from dataclasses import dataclass
from struct import pack,pack_into,unpack_from
import json,zlib,sys,bisect,math
import numpy as np
from PIL import Image,ImageDraw,ImageOps,ImageFont
import cels as C

R=Path(__file__).resolve().parent
P=R.parents[2]
OUT=R.parent
SIZE=(36,86)
BG=Image.open(OUT/'Alisa_scene_background.png').convert('RGBA')
LAYER_NAMES=('задняя нога','таз','передняя нога','юбка','кофта','голова')

def shadow_offset(clip,i):
 amount=4 if clip.name.endswith('_back') else 2
 if clip.name.startswith(('idle','turn')):return 0
 if clip.name.startswith('walk'):return -amount
 progress=i/8 if clip.name.startswith('start') else 1-i/8
 return -C.pixel_round(amount*progress)

def contacts(clip,i):
 name=clip.name
 if name.startswith('turn'):
  src,dst={'turn_back_right':('back','back_right'),'turn_right_back':('back_right','back'),
           'turn_back_left':('back','back_left'),'turn_left_back':('back_left','back')}[name]
  c=C.BANK['idle_'+(src if i<3 else dst)]
  pts=contacts(c,0)
  return [(x+18-c.pivot,y) for x,y in pts]
 diagonal=not name.endswith('_back');mirror=name.endswith('_left');pts=[]
 if name.startswith('idle'):
  pts=[(22,85),(11,84)] if diagonal else [(12,85),(23,85)]
 elif name.startswith('walk'):
  j=(i+8)%16
  if i<=8:pts.append((C.NE_POSES[i][6],C.NE_POSES[i][7]) if diagonal else (12,C.N_POSES[i][7]))
  if j<=8:pts.append((C.NE_POSES[j][6]-6,C.NE_POSES[j][7]-1) if diagonal else (23,C.N_POSES[j][7]))
 elif name.startswith('start'):
  pts=[((11 if i<7 else 10 if i==7 else 9),84)] if diagonal else [(23,85)]
  if i==8:pts.append((31,81) if diagonal else (12,77))
 elif name.startswith('stop'):
  if diagonal:
   pts=[((31,29,27,26,25,24,23,22,22)[i],81+i//2)]
   if i>=7:pts.append((11,(84,83,81,80,80,81,82,83,84)[i]))
  else:
   pts=[(12,77+i)]
   if i>=7:pts.append((23,84 if i==7 else 85))
 return [(35-x,y) for x,y in pts] if mirror else pts

def chunk(kind,data):return pack('<IH',len(data)+6,kind)+data

def export():
 total=sum(len(c.cels) for c in C.CLIPS);atlas=Image.new('RGBA',(360,86*((total+9)//10)))
 entries=[];tags=[];flat=[];n=0
 for clip in C.CLIPS:
  speed={'x':clip.cycle[0]/.96,'y':clip.cycle[1]/.96} if clip.name.startswith('walk') else {'x':0,'y':0}
  tags.append({'name':clip.name,'from':n,'to':n+len(clip.cels)-1,'direction':'forward','repeat':0 if clip.loop else 1,
               'loop':clip.loop,'pivot':{'x':clip.pivot,'y':85},'velocityPxPerSecond':speed,'rootCycleDisplacement':list(clip.cycle)})
  for i,(layers,ms) in enumerate(zip(clip.cels,clip.durations)):
   im=C.flatten(layers);x=n%10*36;y=n//10*86;atlas.paste(im,(x,y))
   entries.append({'filename':f'{clip.name}_{i:02}.png','frame':{'x':x,'y':y,'w':36,'h':86},'duration':ms,'rotated':False,'trimmed':False,
                   'sourceSize':{'w':36,'h':86},'spriteSourceSize':{'x':0,'y':0,'w':36,'h':86},'rootOffset':list(clip.offsets[i]),
                   'footContacts':[list(p) for p in contacts(clip,i)],'shadowOffsetY':shadow_offset(clip,i)})
   flat.append((layers,im,ms));n+=1
 atlas.save(OUT/'Alisa_back_polished_atlas.png',optimize=True)
 meta={'image':'Alisa_back_polished_atlas.png','format':'RGBA8888','size':{'w':atlas.width,'h':atlas.height},'scale':'1','positionRounding':'floor(value+0.5)',
       'frameTags':tags,'layers':[{'name':name,'opacity':255,'blendMode':'normal'} for name in LAYER_NAMES]}
 (OUT/'Alisa_back_polished.json').write_text(json.dumps({'frames':entries,'meta':meta},ensure_ascii=False,indent=2),encoding='utf-8')
 td=pack('<H8x',len(tags))
 for t in tags:
  name=t['name'].encode();td+=pack('<HHBH6x3BBH',t['from'],t['to'],0,t['repeat'],128,188,220,0,len(name))+name
 frames=[]
 for k,(layers,im,ms) in enumerate(flat):
  cs=[]
  if k==0:
   for name in LAYER_NAMES:
    s=name.encode();cs.append(chunk(0x2004,pack('<6HB3xH',3,0,0,0,0,0,255,len(s))+s))
   cs.append(chunk(0x2018,td))
  for i,layer in enumerate(layers):cs.append(chunk(0x2005,pack('<HhhBHh5xHH',i,0,0,255,2,0,36,86)+zlib.compress(layer.tobytes(),9)))
  data=b''.join(cs);frames.append(pack('<IHHH2xI',len(data)+16,0xF1FA,len(cs),ms,0)+data)
 data=b''.join(frames);header=bytearray(128)
 pack_into('<IHHHHHIH',header,0,len(data)+128,0xA5E0,total,36,86,32,1,60);header[34:36]=bytes((1,1))
 doc=header+data;(OUT/'Alisa_back_polished.aseprite').write_bytes(doc)
 pos=128
 for k,(layers,im,ms) in enumerate(flat):
  length,magic,num,duration=unpack_from('<IHHH',doc,pos);end=pos+length;pos+=16;decoded={}
  assert magic==0xF1FA and duration==ms
  for _ in range(num):
   size,kind=unpack_from('<IH',doc,pos)
   if kind==0x2005:
    layer=unpack_from('<H',doc,pos+6)[0];decoded[layer]=Image.frombytes('RGBA',SIZE,zlib.decompress(doc[pos+26:pos+size]))
   pos+=size
  assert pos==end and len(decoded)==6
  comp=C.flatten([decoded[i] for i in range(6)])
  assert comp.tobytes()==im.tobytes()==atlas.crop((k%10*36,k//10*86,k%10*36+36,k//10*86+86)).tobytes()
 assert pos==len(doc)
 print('Native export verified:',total,'frames;',len(tags),'tags; six layers;',atlas.size,flush=True)

def actor(layers,pivot):
 out=Image.new('RGBA',(56,94));out.alpha_composite(C.flatten(layers),(28-pivot,4));return out

def validate():
 for direction in ('back','back_right','back_left'):
  idle,start,walk,stop=[C.BANK[state+'_'+direction] for state in ('idle','start','walk','stop')]
  assert C.flatten(idle.cels[0]).tobytes()==C.flatten(start.cels[0]).tobytes()==C.flatten(stop.cels[-1]).tobytes()
  assert C.flatten(walk.cels[0]).tobytes()==C.flatten(start.cels[-1]).tobytes()==C.flatten(stop.cels[0]).tobytes()
 for clip in C.CLIPS:
  for i,layers in enumerate(clip.cels):
   im=C.flatten(layers);a=np.asarray(im)
   assert im.size==SIZE and set(np.unique(a[:,:,3]))<={0,255}
   for x,y in contacts(clip,i):assert im.getpixel((x,y))[3]>0,(clip.name,i,x,y)
 for clip in C.CLIPS:
  if not clip.name.startswith('turn'):continue
  src,dst={'turn_back_right':('back','back_right'),'turn_right_back':('back_right','back'),
           'turn_back_left':('back','back_left'),'turn_left_back':('back_left','back')}[clip.name]
  a=C.BANK['idle_'+src];b=C.BANK['idle_'+dst]
  assert actor(clip.cels[0],clip.pivot).tobytes()==actor(a.cels[0],a.pivot).tobytes()
  assert actor(clip.cels[-1],clip.pivot).tobytes()==actor(b.cels[0],b.pivot).tobytes()
 # Verify planted heels against the actual exported root motion, including stops.
 for direction in ('back','back_right'):
  walk=C.BANK['walk_'+direction];stop=C.BANK['stop_'+direction];start=C.BANK['start_'+direction]
  for clip in (walk,stop):
   positions=[]
   for i in range(9):
    x,y=contacts(clip,i)[0];dx,dy=clip.offsets[i]
    positions.append((C.pixel_round(dx)+x,C.pixel_round(dy)+y))
   assert len(set(positions))==1,(clip.name,positions)
  positions=[]
  for i in range(9):
   x,y=contacts(start,i)[0];dx,dy=start.offsets[i];positions.append((C.pixel_round(dx)+x,C.pixel_round(dy)+y))
  assert len(set(positions))==1,(start.name,positions)
  landing=[]
  for i in (7,8):
   x,y=contacts(stop,i)[1];dx,dy=stop.offsets[i];landing.append((C.pixel_round(dx)+x,C.pixel_round(dy)+y))
  assert landing[0]==landing[1],(direction,landing)
 right=C.BANK['walk_back_right'];left=C.BANK['walk_back_left']
 for r,l in zip(right.cels,left.cels):assert C.flatten(l).tobytes()==ImageOps.mirror(C.flatten(r)).tobytes()
 base=np.asarray(C.DIAGONAL.head);yy,xx=np.indices((86,36));rgb=base[:,:,:3].astype(int)
 cheek=(base[:,:,3]>0)&(xx>=24)&(rgb[:,:,0]>150)&(rgb[:,:,0]-rgb[:,:,2]>15)
 for i,layers in enumerate(C.DIAGONAL.walk_layers):
  head=np.asarray(layers[5]);hb=C.HEAD_BOB[i]
  for y,x in np.argwhere(cheek):assert np.array_equal(head[y+hb,x],base[y,x])
  if C.HAIR[i]<0:
   for y in range(24,30):
    if base[y,23,3]:assert head[y+hb,23,3]>0
 print('Start/stop and turn endpoints exact. Planted feet stay fixed during stride and deceleration.',flush=True)

@dataclass
class Cel:
 start:int
 duration:int
 clip:str
 index:int
 x:float
 y:float

class Scene:
 def __init__(self,x=120.,y=212.):self.x=x;self.y=y;self.time=0;self.cels=[]
 def add(self,name,i,ms=None,x=None,y=None):
  clip=C.BANK[name];ms=clip.durations[i] if ms is None else ms
  assert ms%20==0
  self.cels.append(Cel(self.time,ms,name,i,self.x if x is None else x,self.y if y is None else y));self.time+=ms
 def sequence(self,name,skip=0):
  clip=C.BANK[name];bx,by=self.x,self.y
  for i in range(skip,len(clip.cels)):
   dx,dy=clip.offsets[i];self.add(name,i,x=bx+dx,y=by+dy)
  dx,dy=clip.offsets[-1];self.x=bx+dx;self.y=by+dy
 def walk(self,direction,cycles=2):
  name='walk_'+direction;clip=C.BANK[name];n=len(clip.cels);dx,dy=clip.cycle[0]/n,clip.cycle[1]/n
  for j in range(1,n*cycles+1):
   self.x+=dx;self.y+=dy;self.add(name,j%n)
 def at(self,t):
  starts=[c.start for c in self.cels];return self.cels[min(len(starts)-1,bisect.bisect_right(starts,t)-1)]

SCENE=Scene()
for i,ms in ((0,600),(1,300),(2,300)):SCENE.add('idle_back',i,ms)
SCENE.sequence('start_back');SCENE.walk('back');SCENE.sequence('stop_back',1);SCENE.add('idle_back',0,400)
SCENE.sequence('turn_back_right');SCENE.add('idle_back_right',0,160)
SCENE.sequence('start_back_right');SCENE.walk('back_right');SCENE.sequence('stop_back_right',1);SCENE.add('idle_back_right',0,400)
SCENE.sequence('turn_right_back');SCENE.sequence('turn_back_left');SCENE.add('idle_back_left',0,160)
SCENE.sequence('start_back_left');SCENE.walk('back_left');SCENE.sequence('stop_back_left',1);SCENE.sequence('idle_back_left')
TOTAL=SCENE.time

def draw_actor(bg,cel):
 clip=C.BANK[cel.clip];x,y=C.pixel_round(cel.x),C.pixel_round(cel.y);out=bg.copy()
 sh=Image.new('RGBA',bg.size);d=ImageDraw.Draw(sh);sy=shadow_offset(clip,cel.index)
 d.ellipse((x-11,y+sy-2,x+11,y+sy+2),fill=(18,20,28,55))
 for fx,fy in contacts(clip,cel.index):
  xx=x-clip.pivot+fx;yy=y-85+fy
  d.ellipse((xx-2,yy-1,xx+2,yy+1),fill=(18,20,28,65))
 out.alpha_composite(sh);out.alpha_composite(C.flatten(clip.cels[cel.index]),(x-clip.pivot,y-85))
 return out.convert('RGB')

def render(t):return draw_actor(BG,SCENE.at(t))

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
 gif([triptych([C.flatten(C.BANK['walk_'+d].cels[i]) for d in ('back_right','back','back_left')]) for i in range(16)],[60]*16,OUT/'Alisa_back_polished_walk.gif')
 gif([triptych([C.flatten(C.BANK['idle_'+d].cels[i]) for d in ('back_right','back','back_left')]) for i in range(4)],C.IDLE_MS,OUT/'Alisa_back_polished_idle.gif')
 # This preview includes root movement and the floor, so the closing step can
 # be judged without mistaking its relative foot motion for ground sliding.
 minis=[]
 for direction,x in (('back_right',32),('back',64),('back_left',96)):
  scene=Scene(x,132);scene.add('idle_'+direction,0,500);scene.sequence('start_'+direction);scene.walk(direction,1);scene.sequence('stop_'+direction,1);scene.add('idle_'+direction,0,600);minis.append(scene)
 ground=BG.crop((0,70,128,214));ims=[]
 for t in range(0,minis[0].time,20):
  b=Image.new('RGB',(384,144))
  for n,s in enumerate(minis):b.paste(draw_actor(ground,s.at(t)),(n*128,0))
  ims.append(b.resize((1152,432),Image.Resampling.NEAREST))
 gif(ims,[20]*len(ims),OUT/'Alisa_back_polished_transitions.gif')
 # Actual old/new timings on the same enlarged canvas; old sprites untouched.
 old=Image.open(P/'alisa/back_walk/Alisa_back_atlas.png').convert('RGBA');oldmeta=json.loads((P/'alisa/back_walk/Alisa_back.json').read_text(encoding='utf-8'))
 tag=next(t for t in oldmeta['meta']['frameTags'] if t['name']=='walk_back');oldframes=[]
 for i in range(tag['from'],tag['to']+1):
  f=oldmeta['frames'][i]['frame'];oldframes.append(old.crop((f['x'],f['y'],f['x']+36,f['y']+86)))
 try:font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
 except OSError:font=ImageFont.load_default()
 ims=[]
 for t in range(0,3000,20):
  bg=Image.new('RGBA',(100,108),(105,99,112,255));bg.alpha_composite(oldframes[t//100%10],(7,6));bg.alpha_composite(C.flatten(C.BACK.walk_layers[t//60%16]),(57,6))
  b=bg.resize((600,648),Image.Resampling.NEAREST).convert('RGB');d=ImageDraw.Draw(b);d.text((80,596),'Было',font=font,fill='white');d.text((380,596),'Стало',font=font,fill='white');ims.append(b)
 gif(ims,[20]*len(ims),OUT/'Alisa_back_before_after.gif')
 model=Image.new('RGBA',(144,96),(105,99,112,255));side=Image.open(P/'alisa/side_walk/Alisa_side_idle.png').convert('RGBA')
 for i,im in enumerate((side,C.flatten(C.DIAGONAL.idle_layers[0]),C.flatten(C.BACK.idle_layers[0]),C.flatten(C.mirrored(C.DIAGONAL.idle_layers[0])))):model.alpha_composite(im,(i*36,5))
 model.resize((1152,768),Image.Resampling.NEAREST).save(OUT/'Alisa_back_polished_model.png')
 render(3000).resize((1280,960),Image.Resampling.NEAREST).save(OUT/'Alisa_back_polished_poster.png')
 timeline={'durationMs':TOTAL,'fps':50,'spriteSize':[36,86],'timeline':[{'startMs':c.start,'durationMs':c.duration,'clip':c.clip,'frame':c.index,'position':[c.x,c.y]} for c in SCENE.cels]}
 (OUT/'Alisa_back_polished_timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
 board=Image.new('RGB',(1280,520),(40,42,50));d=ImageDraw.Draw(board)
 for i,t in enumerate((0,1700,3000,4900,6100,8600,10400,TOTAL-500)):
  xx=i%4*320;yy=i//4*260;board.paste(render(t),(xx,yy));d.text((xx+5,yy+243),f'{t/1000:.2f}s {SCENE.at(t).clip}',fill='white')
 board.save(R/'review_scene.png')
 print('Scene:',TOTAL/1000,'s;',TOTAL//20,'video frames.',flush=True)

M=np.array([[65.481,128.553,24.966],[-37.797,-74.203,112.0],[112.0,-93.786,-18.214]],np.float32)/255
def yuv(im):
 a=np.rint(np.asarray(im).astype(np.float32)@M.T+[16,128,128]).astype(np.uint8)
 return (a[:,:,0].repeat(4,0).repeat(4,1),a[:,:,1].repeat(2,0).repeat(2,1),a[:,:,2].repeat(2,0).repeat(2,1))
def planes():
 for t in range(0,TOTAL,20):yield yuv(render(t))
def verify_video():
 from refdecode import decode_reference
 count=0;err=0
 for n,(t,actual) in enumerate(decode_reference(OUT/'Alisa_back_polished.mp4',raw=True)):
  assert abs(t-n*.02)<1e-6 and actual[0].shape==(960,1280)
  if n%25==0:
   for a,b in zip(yuv(render(n*20)),actual):err=max(err,int(np.abs(a.astype(np.int16)-b.astype(np.int16)).max()))
  count+=1
 assert count==TOTAL//20 and err<=6,(count,err)
 print('Video verified:',count,'frames;',TOTAL/1000,'s; max sampled YUVerror',err,flush=True)

if __name__=='__main__':
 export();validate();previews()
 if '--render' in sys.argv:
  from encode import encode
  encode(planes(),OUT/'Alisa_back_polished.mp4',1280,960,50);verify_video()
 elif '--verify-video' in sys.argv:verify_video()
