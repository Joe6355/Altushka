"""Export the redrawn key-pose study and the rear in-place loop."""
from pathlib import Path
from struct import pack,pack_into,unpack_from
import json,zlib,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import redraw as C

R=Path(__file__).resolve().parent
P=R.parents[2]
OUT=R.parent
NAMES=('правая нога','левая нога','юбка','кофта','голова')
CLIPS=[('key_poses_back',C.KEY_LAYERS,[240]*4,False),('walk_back',C.WALK_LAYERS,[120]*8,True)]

def chunk(k,data):return pack('<IH',len(data)+6,k)+data
def export():
 atlas=Image.new('RGBA',(144,258));tags=[];entries=[];flat=[];n=0
 for name,cels,durations,loop in CLIPS:
  tags.append({'name':name,'from':n,'to':n+len(cels)-1,'direction':'forward','loop':loop,'repeat':0 if loop else 1,'pivot':{'x':18,'y':85},'rootMotion':'in_place'})
  for i,(layers,ms) in enumerate(zip(cels,durations)):
   im=C.flatten(layers);x=n%4*36;y=n//4*86;atlas.paste(im,(x,y))
   entries.append({'filename':f'{name}_{i:02}.png','frame':{'x':x,'y':y,'w':36,'h':86},'duration':ms,'sourceSize':{'w':36,'h':86},'spriteSourceSize':{'x':0,'y':0,'w':36,'h':86},'trimmed':False,'rotated':False})
   flat.append((layers,im,ms));n+=1
 atlas.save(OUT/'Alisa_rear_redrawn_atlas.png',optimize=True)
 meta={'image':'Alisa_rear_redrawn_atlas.png','format':'RGBA8888','size':{'w':144,'h':258},'scale':'1','frameTags':tags,'layers':[{'name':name,'opacity':255,'blendMode':'normal'} for name in NAMES]}
 (OUT/'Alisa_rear_redrawn.json').write_text(json.dumps({'frames':entries,'meta':meta},ensure_ascii=False,indent=2),encoding='utf-8')
 data=pack('<H8x',len(tags))
 for t in tags:
  s=t['name'].encode();data+=pack('<HHBH6x3BBH',t['from'],t['to'],0,t['repeat'],128,188,220,0,len(s))+s
 tagchunk=chunk(0x2018,data);frames=[]
 for i,(layers,im,ms) in enumerate(flat):
  cs=[]
  if i==0:
   for name in NAMES:
    s=name.encode();cs.append(chunk(0x2004,pack('<6HB3xH',3,0,0,0,0,0,255,len(s))+s))
   cs.append(tagchunk)
  for layer,part in enumerate(layers):cs.append(chunk(0x2005,pack('<HhhBHh5xHH',layer,0,0,255,2,0,36,86)+zlib.compress(part.tobytes(),9)))
  raw=b''.join(cs);frames.append(pack('<IHHH2xI',len(raw)+16,0xF1FA,len(cs),ms,0)+raw)
 raw=b''.join(frames);header=bytearray(128);pack_into('<IHHHHHIH',header,0,len(raw)+128,0xA5E0,len(flat),36,86,32,1,120);header[34:36]=bytes((1,1))
 doc=header+raw;(OUT/'Alisa_rear_redrawn.aseprite').write_bytes(doc)
 pos=128
 for i,(layers,im,ms) in enumerate(flat):
  size,magic,num,duration=unpack_from('<IHHH',doc,pos);end=pos+size;pos+=16;read={}
  assert magic==0xF1FA and duration==ms
  for _ in range(num):
   length,kind=unpack_from('<IH',doc,pos)
   if kind==0x2005:
    index=unpack_from('<H',doc,pos+6)[0];read[index]=Image.frombytes('RGBA',(36,86),zlib.decompress(doc[pos+26:pos+length]))
   pos+=length
  assert pos==end and len(read)==5
  assert C.flatten([read[i] for i in range(5)]).tobytes()==im.tobytes()==atlas.crop((i%4*36,i//4*86,i%4*36+36,i//4*86+86)).tobytes()
 assert pos==len(doc)
 for im in C.WALK:
  a=np.asarray(im);assert im.size==(36,86) and set(np.unique(a[:,:,3]))<={0,255}
 assert len(C.WALK)==8
 print('Native export verified:12frames,2tags,5layers,36x86.',flush=True)

def save_gif(images,durations,path):
 rgb=[im.convert('RGB') for im in images]
 palette=Image.fromarray(np.vstack([np.asarray(im) for im in rgb])).quantize(colors=240,method=Image.Quantize.MEDIANCUT)
 ims=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in rgb]
 ims[0].save(path,save_all=True,append_images=ims[1:],duration=durations,loop=0,disposal=2)

BG=Image.open(OUT/'Alisa_scene_background.png').convert('RGBA').crop((112,96,208,208))
TOTAL=4800
def render(n):
 im=C.WALK[(n//6)%8]
 bg=BG.copy();sh=Image.new('RGBA',BG.size)
 ImageDraw.Draw(sh).ellipse((36,98,60,102),fill=(18,20,28,60));bg.alpha_composite(sh)
 bg.alpha_composite(im,(30,15))
 return bg.convert('RGB')

def previews():
 C.proof()
 ims=[]
 for im in C.WALK:
  bg=Image.new('RGBA',(60,96),(105,99,112,255));bg.alpha_composite(im,(12,5))
  ims.append(bg.resize((360,576),Image.Resampling.NEAREST).convert('RGB'))
 save_gif(ims,[120]*8,OUT/'Alisa_rear_redrawn.gif')
 render(0).resize((576,672),Image.Resampling.NEAREST).save(OUT/'Alisa_rear_redrawn_poster.png')
 # Equal960ms cycle duration, shown with the original frame timing of each.
 old=Image.open(P/'alisa/back_walk_polished/Alisa_back_polished_atlas.png').convert('RGBA')
 data=json.loads((P/'alisa/back_walk_polished/Alisa_back_polished.json').read_text(encoding='utf-8'))
 tag=next(t for t in data['meta']['frameTags'] if t['name']=='walk_back');oldims=[]
 for i in range(tag['from'],tag['to']+1):
  f=data['frames'][i]['frame'];oldims.append(old.crop((f['x'],f['y'],f['x']+36,f['y']+86)))
 try:font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
 except OSError:font=ImageFont.load_default()
 compare=[]
 for t in range(0,1920,20):
  bg=Image.new('RGBA',(100,106),(105,99,112,255));bg.alpha_composite(oldims[t//60%16],(7,5));bg.alpha_composite(C.WALK[t//120%8],(57,5))
  b=bg.resize((600,636),Image.Resampling.NEAREST).convert('RGB');d=ImageDraw.Draw(b);d.text((80,584),'Было',font=font,fill='white');d.text((350,584),'Новая основа',font=font,fill='white');compare.append(b)
 save_gif(compare,[20]*len(compare),OUT/'Alisa_rear_comparison.gif')
 print('Rear in-place cycle:8drawn cels,960ms; scene4.8s.',flush=True)

M=np.array([[65.481,128.553,24.966],[-37.797,-74.203,112.0],[112.0,-93.786,-18.214]],np.float32)/255
def yuv(im):
 a=np.rint(np.asarray(im).astype(np.float32)@M.T+[16,128,128]).astype(np.uint8)
 return (a[:,:,0].repeat(6,0).repeat(6,1),a[:,:,1].repeat(3,0).repeat(3,1),a[:,:,2].repeat(3,0).repeat(3,1))
def planes():
 for n in range(240):yield yuv(render(n))
def verify_video():
 from refdecode import decode_reference
 count=0;error=0
 for n,(t,actual) in enumerate(decode_reference(OUT/'Alisa_rear_redrawn.mp4',raw=True)):
  assert abs(t-n*.02)<1e-6 and actual[0].shape==(672,576)
  if n%12==0:
   for a,b in zip(yuv(render(n)),actual):error=max(error,int(np.abs(a.astype(np.int16)-b.astype(np.int16)).max()))
  count+=1
 assert count==240 and error<=6,(count,error)
 print('Video verified:240frames,4.8s; max sampled YUVerror',error,flush=True)

if __name__=='__main__':
 export();previews()
 if '--render' in sys.argv:
  from encode import encode
  encode(planes(),OUT/'Alisa_rear_redrawn.mp4',576,672,50);verify_video()
 elif '--verify-video' in sys.argv:verify_video()
