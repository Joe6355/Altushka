"""Export the side-view study without modifying previously accepted assets."""
from pathlib import Path
from struct import pack,pack_into,unpack_from
import json,zlib,sys
import numpy as np
from PIL import Image,ImageDraw,ImageOps
import profile as C

R=Path(__file__).resolve().parent
P=R.parents[2]
OUT=R.parent
SIZE=(36,86)
CLIPS=[
 ('idle_side_right',C.IDLE_LAYERS,C.IDLE_MS,18),
 ('walk_side_right',C.WALK_LAYERS,[100]*10,18),
 ('idle_side_left',[C.mirror_layers(im) for im in C.IDLE_LAYERS],C.IDLE_MS,17),
 ('walk_side_left',[C.mirror_layers(im) for im in C.WALK_LAYERS],[100]*10,17),
]
LAYER_NAMES=('дальняя нога','таз','ближняя нога','юбка','кофта','голова')

def chunk(kind,data):return pack('<IH',len(data)+6,kind)+data

def export():
 total=sum(len(cels) for _,cels,_,_ in CLIPS)
 atlas=Image.new('RGBA',(360,86*((total+9)//10)))
 flat=[];entries=[];tags=[];n=0
 for name,cels,durations,pivot in CLIPS:
  tags.append({'name':name,'from':n,'to':n+len(cels)-1,'direction':'forward','repeat':0,'loop':True,'pivot':{'x':pivot,'y':85},'velocityPxPerSecond':{'x':(40 if name.endswith('right') else -40) if name.startswith('walk') else 0,'y':0}})
  for i,(layers,ms) in enumerate(zip(cels,durations)):
   im=C.flatten(layers);x=n%10*36;y=n//10*86;atlas.paste(im,(x,y))
   entries.append({'filename':f'{name}_{i:02}.png','frame':{'x':x,'y':y,'w':36,'h':86},'duration':ms,'trimmed':False,'rotated':False,'sourceSize':{'w':36,'h':86},'spriteSourceSize':{'x':0,'y':0,'w':36,'h':86}})
   flat.append((layers,im,ms));n+=1
 atlas.save(OUT/'Alisa_side_atlas.png',optimize=True)
 meta={'image':'Alisa_side_atlas.png','format':'RGBA8888','size':{'w':atlas.width,'h':atlas.height},'scale':'1','frameTags':tags,'layers':[{'name':name,'opacity':255,'blendMode':'normal'} for name in LAYER_NAMES]}
 (OUT/'Alisa_side.json').write_text(json.dumps({'frames':entries,'meta':meta},ensure_ascii=False,indent=2),encoding='utf-8')
 tagdata=pack('<H8x',len(tags))
 for tag in tags:
  name=tag['name'].encode('utf-8')
  tagdata+=pack('<HHBH6x3BBH',tag['from'],tag['to'],0,0,128,188,220,0,len(name))+name
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
 doc=header+data;(OUT/'Alisa_side.aseprite').write_bytes(doc)
 # Read each exported layer and composite it independently before comparison.
 pos=128
 for n,(layers,im,ms) in enumerate(flat):
  length,magic,num,duration=unpack_from('<IHHH',doc,pos);end=pos+length;pos+=16
  assert magic==0xF1FA and duration==ms
  readlayers={}
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

def gif(images,durations,path):
 rgb=[im.convert('RGB') for im in images]
 palette=Image.fromarray(np.vstack([np.asarray(im) for im in rgb])).quantize(colors=240,method=Image.Quantize.MEDIANCUT)
 q=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in rgb]
 q[0].save(path,save_all=True,append_images=q[1:],duration=durations,loop=0,disposal=2)

def paired(im):
 bg=Image.new('RGBA',(100,98),(105,99,112,255))
 bg.alpha_composite(im,(7,6));bg.alpha_composite(ImageOps.mirror(im),(57,6))
 return bg.resize((600,588),Image.Resampling.NEAREST).convert('RGB')

BG=Image.open(OUT/'Alisa_scene_background.png').convert('RGBA')
def render(n):
 i=(n//5)%10;step=n//5
 x=58+4*step;y=172
 bg=BG.copy();shadow=Image.new('RGBA',BG.size)
 ImageDraw.Draw(shadow).ellipse((x-12,y-2,x+12,y+2),fill=(18,20,28,60));bg.alpha_composite(shadow)
 bg.alpha_composite(C.WALK[i],(x-18,y-85))
 return bg.convert('RGB')

def previews():
 gif([paired(im) for im in C.WALK],[100]*10,OUT/'Alisa_side_walk.gif')
 gif([paired(im) for im in C.IDLE],C.IDLE_MS,OUT/'Alisa_side_idle.gif')
 C.IDLE[0].save(OUT/'Alisa_side_idle.png')
 review=Image.new('RGBA',(108,96),(105,99,112,255))
 original=Image.open(P/'recolor/blue_eyes/Altushka_blue_atlas.png').convert('RGBA').crop((144,0,180,86))
 stable=C.blank();stable.paste(original,(3,0))
 for n,im in enumerate((stable,C.IDLE[0],C.WALK[0])):review.alpha_composite(im,(n*36,5))
 review.resize((864,768),Image.Resampling.NEAREST).save(OUT/'Alisa_side_model.png')
 render(110).resize((1280,960),Image.Resampling.NEAREST).save(OUT/'Alisa_side_walk_poster.png')

def validate():
 # A planted toe remains on one exact native ground pixel during stance.
 toes=np.array([34,30,26,22,18,14]);world=toes+np.arange(6)*4
 assert np.ptp(world)==0
 for i in range(6):
  a=np.asarray(C.leg(i));assert a[85,toes[i],3]==255
 # Every pose has a planted foot; no semi-transparent native pixels.
 for i,layers in enumerate(C.WALK_LAYERS):
  im=C.flatten(layers);a=np.asarray(im)
  assert im.size==SIZE and set(np.unique(a[:,:,3]))<={0,255}
  assert a[84:86,:,3].any()
  head=np.asarray(layers[-1]);ref=np.asarray(C.shift(C.HEAD,0,C.BOB[i]))
  assert np.array_equal(head[8:],ref[8:])
  assert tuple(head[20+C.BOB[i],24])==(*C.PALETTE[17],255)
  # Check the authored contours before they reach a clipped image canvas.
  for x,y in C.LEG[i]:assert 0<=x<36 and 0<=y<86
  for x,y in C.LEG[(i+5)%10]:assert 0<=x-2<36 and 0<=y-1<86
 for i in range(10):
  assert C.flatten(C.mirror_layers(C.WALK_LAYERS[i])).tobytes()==ImageOps.mirror(C.WALK[i]).tobytes()
 print('Native36x86; profile face consistent; planted toe drift0px; mirrored directions exact.',flush=True)

M=np.array([[65.481,128.553,24.966],[-37.797,-74.203,112.0],[112.0,-93.786,-18.214]],np.float32)/255
def yuv(im):
 a=np.rint(np.asarray(im).astype(np.float32)@M.T+[16,128,128]).astype(np.uint8)
 return (a[:,:,0].repeat(4,0).repeat(4,1),a[:,:,1].repeat(2,0).repeat(2,1),a[:,:,2].repeat(2,0).repeat(2,1))

def planes():
 for n in range(250):yield yuv(render(n))

def verify_video():
 from refdecode import decode_reference
 count=0;err=0
 for n,(t,actual) in enumerate(decode_reference(OUT/'Alisa_side_walk.mp4',raw=True)):
  assert abs(t-n*.02)<1e-6 and actual[0].shape==(960,1280)
  if n%25==0:
   for a,b in zip(yuv(render(n)),actual):err=max(err,int(np.abs(a.astype(np.int16)-b.astype(np.int16)).max()))
  count+=1
 assert count==250 and err<=6,(count,err)
 print('Video verified:250frames;5s; sampled max YUVerror',err,flush=True)

if __name__=='__main__':
 export();validate();previews()
 if '--render' in sys.argv:
  from encode import encode
  encode(planes(),OUT/'Alisa_side_walk.mp4',1280,960,50)
  verify_video()
 elif '--verify-video' in sys.argv:verify_video()
