"""Import generated pose drawings onto Alisa's native grid and export game assets.

Raster artwork comes from image_gen. This importer only registers/samples those
drawings, maps the source palette, mirrors directions, and packages animation cels.
One anatomical calibration per orientation is shared by all of its poses.
"""
from pathlib import Path
from struct import pack, pack_into, unpack_from
import json
import zlib
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = HERE.parents[2]
SIZE = (36, 86)
PAL = np.array([
    (2,2,2),(24,24,29),(34,34,38),(43,43,48),(55,55,60),
    (70,70,78),(139,139,150),(164,164,174),(190,190,200),
    (213,213,223),(232,232,239),(244,244,248),(255,255,255),
    (255,242,231),(247,186,188),(229,145,158),(212,112,135),
    (55,183,226),(139,232,245),(39,92,128)], dtype=np.int32)
IDLE_MS = [900, 400, 100, 1000]
WALK_MS = [100] * 8
VIEWS = {'e':'Side', 'n':'North', 's':'South', 'ne':'NorthEast', 'se':'SouthEast'}
ORDER = ('s','se','e','ne','n','nw','w','sw')
LABELS = {'s':'Вниз','se':'Вниз-вправо','e':'Вправо','ne':'Вверх-вправо',
          'n':'Вверх','nw':'Вверх-влево','w':'Влево','sw':'Вниз-влево'}


def bands(projection, gap=10, minimum=20):
    points = np.flatnonzero(projection)
    groups = []
    for point in points:
        point = int(point)
        if not groups or point - groups[-1][1] > gap + 1:
            groups.append([point, point])
        else:
            groups[-1][1] = point
    return [(a, b+1) for a,b in groups if b-a+1 >= minimum]


def landmarks(part):
    alpha = part[:,:,3] >= 128
    yy, xx = np.where(alpha)
    height = int(yy.max()-yy.min()+1)
    rgb = part[:,:,:3].astype(np.int32)
    neutral = alpha & (rgb.min(2) > 95) & (np.ptp(rgb,axis=2) < 23)
    runs = bands(neutral.sum(1) >= 3, gap=max(2,height//80), minimum=5)
    skirts = [(a,b) for a,b in runs if a > yy.min()+height*.38 and a < yy.min()+height*.7]
    assert skirts, ('No skirt band', runs, height)
    waist, hem = max(skirts, key=lambda ab: int(neutral[ab[0]:ab[1]].sum()))
    hair_runs = [(a,b) for a,b in runs if b < waist]
    assert hair_runs, ('No hair band', runs)
    _, hair_bottom = max(hair_runs, key=lambda ab: ab[1]-ab[0])
    # A thin curl can connect to the bob. Register the crown by its broad white
    # mass, rather than treating the first curl pixel as the whole hair volume.
    head_counts = neutral[:hair_bottom].sum(1)
    broad = np.flatnonzero(head_counts >= max(5, float(head_counts.max())*.45))
    assert len(broad), ('No crown mass', hair_bottom)
    crown = int(broad[0])
    wy, wx = np.where(neutral[waist:min(hem,waist+max(3,(hem-waist)//6))])
    center = float(np.median(wx))
    warm = alpha & (rgb[:,:,0] > 140) & (rgb[:,:,0] - rgb[:,:,2] > 14)
    warm[:hem] = False
    warm[min(part.shape[0],int(hem+height*.13)):] = False
    skin_y = np.where(warm)[0]
    stocking = float(np.quantile(skin_y,.97)+1) if len(skin_y) else hem+height*.04
    stocking = max(hem+2, min(stocking, yy.max()-10))
    return dict(top=float(yy.min()), crown=float(crown), neck=float(hair_bottom),
                waist=float(waist), hem=float(hem), stocking=stocking,
                ground=float(yy.max()), center=center, x0=int(xx.min()), x1=int(xx.max()+1))


def linear_extrapolate(x, xp, fp):
    result = np.interp(x, xp, fp)
    left = x < xp[0]
    result[left] = fp[0] + (x[left]-xp[0])*(fp[1]-fp[0])/(xp[1]-xp[0])
    right = x > xp[-1]
    result[right] = fp[-1] + (x[right]-xp[-1])*(fp[-1]-fp[-2])/(xp[-1]-xp[-2])
    return result


def import_view(name):
    raw = np.array(Image.open(HERE/(name+'_generated.png')).convert('RGBA'))
    mask = raw[:,:,3] >= 128
    cols = bands(mask.sum(0) >= 4, gap=12, minimum=40)
    rows = bands(mask.sum(1) >= 4, gap=12, minimum=150)
    assert len(cols)==4 and len(rows)==3, (name, cols, rows)
    parts = [raw[y0:y1,x0:x1] for y0,y1 in rows for x0,x1 in cols]
    marks = [landmarks(part) for part in parts]
    reference = {key:float(np.median([m[key] for m in marks[:4]]))
                 for key in ('top','crown','neck','waist','hem','stocking','ground')}
    target_y = np.array([2,8,30,44,56,60,85], dtype=float)
    source_y = np.array([reference[k] for k in ('top','crown','neck','waist','hem','stocking','ground')])
    assert np.all(np.diff(source_y)>0), (name, reference)
    scale = (reference['ground']-reference['top'])/83
    # Register each column to its idle waistband; preserve lateral weight shifts in its walk.
    centers = [marks[i]['center'] for i in range(4)]
    left = max((centers[i%4]-m['x0'])/scale for i,m in enumerate(marks))
    right = max((m['x1']-centers[i%4])/scale for i,m in enumerate(marks))
    xscale = scale * max(1.,(left+right)/33)
    left *= scale/xscale
    right *= scale/xscale
    low, high = int(np.ceil(left)), int(np.floor(35-right))
    assert low <= high, (name,left,right,low,high)
    pivot = int(np.clip(18, low, high))
    result = []
    for i,part in enumerate(parts):
        row = i//4
        ground_delta = (rows[row][1]-rows[row][0]-1)-reference['ground']
        sy = np.rint(linear_extrapolate(np.arange(86,dtype=float),target_y,source_y)+ground_delta).astype(int)
        sx = np.rint(centers[i%4]+(np.arange(36,dtype=float)-pivot)*xscale).astype(int)
        a = np.zeros((86,36,4),np.uint8)
        valid_y = (sy>=0)&(sy<part.shape[0]); valid_x=(sx>=0)&(sx<part.shape[1])
        a[np.ix_(valid_y,valid_x)] = part[sy[valid_y,None],sx[None,valid_x]]
        opaque = a[:,:,3]>=128
        colors = a[:,:,:3].astype(np.int32)
        distance = ((colors[:,:,None,:]-PAL[None,None,:,:])**2).sum(3)
        a[:,:,:3] = PAL[distance.argmin(2)].astype(np.uint8)
        a[:,:,3] = opaque.astype(np.uint8)*255
        a[~opaque] = 0
        result.append(Image.fromarray(a))
    calibration = dict(source=str((HERE/(name+'_generated.png')).relative_to(ROOT)),
                       columns=cols, rows=rows, landmarks=reference,
                       targetLandmarks=list(map(int,target_y)),xScale=xscale,pivotX=pivot,pivotY=85)
    return result,pivot,calibration


def chunk(kind,data):
    return pack('<IH',len(data)+6,kind)+data


def parts_for(im):
    a = np.array(im); parts=[]
    for y0,y1 in ((58,86),(44,58),(30,44),(0,30)):
        layer=np.zeros_like(a);layer[y0:y1]=a[y0:y1];parts.append(Image.fromarray(layer))
    return parts


def aseprite(flat,tags,path):
    names=('ноги','юбка и пояс','кофта и руки','голова')
    tagdata=pack('<H8x',len(tags))
    for tag in tags:
        name=tag['name'].encode('utf-8')
        tagdata+=pack('<HHBH6x3BBH',tag['from'],tag['to'],0,0,128,188,220,0,len(name))+name
    records=[]
    for i,(im,ms) in enumerate(flat):
        chunks=[]
        if i==0:
            for name in names:
                encoded=name.encode('utf-8')
                chunks.append(chunk(0x2004,pack('<6HB3xH',3,0,0,0,0,0,255,len(encoded))+encoded))
            chunks.append(chunk(0x2018,tagdata))
        for index,layer in enumerate(parts_for(im)):
            chunks.append(chunk(0x2005,pack('<HhhBHh5xHH',index,0,0,255,2,0,36,86)+zlib.compress(layer.tobytes(),9)))
        data=b''.join(chunks);records.append(pack('<IHHH2xI',len(data)+16,0xF1FA,len(chunks),ms,0)+data)
    data=b''.join(records);header=bytearray(128)
    pack_into('<IHHHHHIH',header,0,len(data)+128,0xA5E0,len(flat),36,86,32,1,100)
    header[34:36]=bytes((1,1));doc=header+data;path.write_bytes(doc)
    offset=128
    for expected,ms in flat:
        size,magic,count,duration=unpack_from('<IHHH',doc,offset);end=offset+size;offset+=16
        assert magic==0xF1FA and duration==ms
        layers={}
        for _ in range(count):
            length,kind=unpack_from('<IH',doc,offset)
            if kind==0x2005:
                index=unpack_from('<H',doc,offset+6)[0]
                layers[index]=Image.frombytes('RGBA',SIZE,zlib.decompress(doc[offset+26:offset+length]))
            offset+=length
        assert offset==end and len(layers)==4
        composite=Image.new('RGBA',SIZE)
        for i in range(4):composite.alpha_composite(layers[i])
        assert composite.tobytes()==expected.tobytes()
    assert offset==len(doc)


def gif(frames,durations,path):
    rgb=[frame.convert('RGB') for frame in frames]
    strip=Image.fromarray(np.vstack([np.array(im) for im in rgb]))
    palette=strip.quantize(colors=240,method=Image.Quantize.MEDIANCUT)
    indexed=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in rgb]
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=durations,loop=0,disposal=2)


def previews(views):
    floor=Image.open(ROOT/'alisa/rear_key_redraw/Alisa_scene_background.png').convert('RGBA')
    positions={'n':(160,99),'ne':(237,113),'e':(272,171),'se':(233,224),
               's':(160,232),'sw':(87,224),'w':(48,171),'nw':(83,113)}
    walk=[]
    for frame in range(8):
        im=floor.copy()
        for direction,(x,y) in positions.items():
            cels,pivot=views[direction]
            im.alpha_composite(cels[4+frame],(x-pivot,y-85))
        walk.append(im.resize((960,720),Image.Resampling.NEAREST).convert('RGB'))
    gif(walk,WALK_MS,OUT/'Alisa_walk_polished.gif')
    walk[0].save(OUT/'Alisa_walk_polished_poster.png')
    idle=[]
    for frame in range(4):
        im=floor.copy()
        for direction,(x,y) in positions.items():
            cels,pivot=views[direction];im.alpha_composite(cels[frame],(x-pivot,y-85))
        idle.append(im.resize((960,720),Image.Resampling.NEAREST).convert('RGB'))
    gif(idle,IDLE_MS,OUT/'Alisa_idle_polished.gif')
    # Unscaled native cels, enlarged strictly with nearest-neighbour for inspection.
    board=Image.new('RGBA',(8*40,5*94),(105,99,112,255))
    for row,direction in enumerate(('s','se','e','ne','n')):
        for i,cel in enumerate(views[direction][0][4:]):board.alpha_composite(cel,(i*40+2,row*94+4))
    board.resize((1600,2350),Image.Resampling.NEAREST).save(OUT/'Alisa_native_walk_review.png')
    rotation=Image.new('RGBA',(8*40,94),(105,99,112,255))
    for i,direction in enumerate(ORDER):rotation.alpha_composite(views[direction][0][0],(i*40+2,4))
    rotation.resize((1600,470),Image.Resampling.NEAREST).save(OUT/'Alisa_turnaround.png')


def main():
    views={};calibration={}
    for direction,name in VIEWS.items():
        cels,pivot,marks=import_view(name)
        views[direction]=(cels,pivot);calibration[direction]=marks
        print(direction,'pivot',pivot,'landmarks',marks['landmarks'],flush=True)
    for target,source in (('w','e'),('nw','ne'),('sw','se')):
        cels,pivot=views[source]
        # Half-cycle shift retains the same anatomical support-leg phase after mirroring.
        mirrored=[ImageOps.mirror(cel) for cel in cels[:4]]
        walking=[ImageOps.mirror(cel) for cel in cels[4:]]
        views[target]=(mirrored+walking[4:]+walking[:4],35-pivot)
    frames=[];tags=[];flat=[]
    atlas=Image.new('RGBA',(288,1032))
    for direction in ORDER:
        cels,pivot=views[direction]
        for kind,indices,durations in (('idle',range(4),IDLE_MS),('walk',range(4,12),WALK_MS)):
            start=len(flat)
            tags.append(dict(name=kind+'_'+direction,**{'from':start,'to':start+len(durations)-1},
                             direction='forward',loop=True,repeat=0,pivot={'x':pivot,'y':85},
                             rootMotion='in_place',label=LABELS[direction]+' — '+('idle' if kind=='idle' else 'ходьба')))
            for local,(index,ms) in enumerate(zip(indices,durations)):
                im=cels[index];n=len(flat);x=n%8*36;y=n//8*86
                assert im.size==SIZE
                a=np.array(im);assert set(np.unique(a[:,:,3]))<={0,255}
                assert a[:,:,3].any() and len(np.unique(a[a[:,:,3]>0,:3],axis=0))<=20
                atlas.paste(im,(x,y));flat.append((im,ms))
                frames.append(dict(filename=f'{kind}_{direction}_{local:02}.png',frame={'x':x,'y':y,'w':36,'h':86},
                                   duration=ms,trimmed=False,rotated=False,sourceSize={'w':36,'h':86},spriteSourceSize={'x':0,'y':0,'w':36,'h':86}))
    assert len(flat)==96 and len(tags)==16
    atlas.save(OUT/'Alisa_motion_polished_atlas.png',optimize=True)
    meta=dict(image='Alisa_motion_polished_atlas.png',format='RGBA8888',size={'w':288,'h':1032},scale='1',frameTags=tags,
              layers=[{'name':name,'opacity':255,'blendMode':'normal'} for name in ('ноги','юбка и пояс','кофта и руки','голова')])
    (OUT/'Alisa_motion_polished.json').write_text(json.dumps({'frames':frames,'meta':meta},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'calibration.json').write_text(json.dumps(calibration,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    aseprite(flat,tags,OUT/'Alisa_motion_polished.aseprite')
    previews(views)
    print('Verified 96 native 36x86 cels, 16 loops, 4 Aseprite layers, binary alpha and original 20-colour palette.',flush=True)


if __name__=='__main__':main()
