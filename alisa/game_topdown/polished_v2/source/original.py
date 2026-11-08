from pathlib import Path
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

root=Path(__file__).parent
atlas=Image.open(Path(__file__).resolve().parent.parents[3]/'recolor'/'blue_eyes'/'Altushka_blue_atlas.png').convert('RGBA')
SIZE=(36,86)
PIVOT=np.array((17.5,43.0))
INK=(0,0,0,255)
STOCK=(43,43,48,255)
STOCK_SHADOW=(28,28,33,255)
STOCK_LIGHT=(55,55,60,255)
SLEEVE=(31,31,37,255)
SLEEVE_SHADOW=(18,18,23,255)
SLEEVE_LIGHT=(51,51,57,255)
SKIN=(255,242,231,255)
SKIN_MID=(247,186,188,255)
SKIN_SHADOW=(215,124,128,255)
SKIRT_COLORS=((212,214,223),(241,242,246),(255,255,255),(250,251,254))

def sprite(index):
    x,y=index%10*36,index//10*86
    return atlas.crop((x,y,x+36,y+86))

def part(img, mask):
    rgba=np.array(img)
    rgba[~mask]=0
    return Image.fromarray(rgba)

def contour(layer):
    edge=layer.getchannel('A').filter(ImageFilter.MaxFilter(3))
    border=Image.new('RGBA',layer.size,INK)
    border.putalpha(edge)
    return Image.alpha_composite(border,layer)

def stamp(img, at, anchor, angle=0):
    target=np.asarray(at,dtype='float64')
    source=np.asarray(anchor,dtype='float64')
    radians=math.radians(angle)
    c,s=math.cos(radians),math.sin(radians)
    rot=np.array(((c,s),(-s,c)))
    shift=source-rot@target
    return img.transform(SIZE,Image.Transform.AFFINE,(c,s,shift[0],-s,c,shift[1]),Image.Resampling.NEAREST)

def head(index, collar, pivot):
    img=sprite(index)
    p=np.array(img)
    yy,xx=np.indices((86,36))
    r,g,b=np.moveaxis(p[:,:,:3].astype('int16'),2,0)
    opaque=p[:,:,3]>0
    lower_hair=(r>=142)&(g>=134)&(np.abs(r-b)<30)
    neck=(r>=101)&(r-g>=21)&(r-b>=12)
    solid=opaque & ((yy<collar) | ((yy<collar+4)&(lower_hair|neck)))
    around=np.asarray(Image.fromarray((solid*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)))>0
    outline=opaque & (r<10)&(g<10)&(b<10)
    mask=solid | (outline & around & (yy<collar+4))
    return stamp(part(img,mask),(17.5,28.0),pivot)

HEADS={
    'still':head(4,26,(15,27)),
    'sway':head(0,27,(18,28)),
    'fast':head(6,28,(15,29)),
    'down':head(7,29,(17,30)),
    'blink':head(18,28,(17,29)),
}

def torso_texture():
    img=sprite(4)
    shape=Image.new('1',SIZE)
    ImageDraw.Draw(shape).polygon([(14,26),(20,26),(23,29),(23,33),(22,36),(22,39),
        (20,43),(10,44),(7,42),(7,39),(5,36),(5,33),(8,31),(10,29)],fill=1)
    p=np.array(img)
    skirt=np.any(np.all(p[:,:,:3,None] == np.array(SKIRT_COLORS).T[None,None,:,:],axis=2),axis=2)
    alpha=(p[:,:,3]>0)&np.asarray(shape)&~skirt
    return stamp(part(img,alpha),(17.5,43),(15,43))

TORSO=torso_texture()

def skirt_texture(index,pivot):
    img=sprite(index)
    p=np.array(img)
    is_fabric=np.any(np.all(p[:,:,:3,None] == np.array(SKIRT_COLORS).T[None,None,:,:],axis=2),axis=2)
    y,_=np.indices((86,36))
    cloth=(y>=41)&(y<=59)&(p[:,:,3]>0)&is_fabric
    near=np.asarray(Image.fromarray((cloth*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)))>0
    rim=(y>=42)&(y<=59)&(p[:,:,3]>0)&(p[:,:,:3].max(axis=2)<10)&near
    return part(img,cloth|rim),pivot

SKIRTS={
    'still':skirt_texture(4,(15,43)),
    'sway':skirt_texture(0,(20,44)),
    'fast':skirt_texture(7,(15,45)),
}
# hip, knee, heel, toe for the two legs on the unrotated 36x86 grid
LEG_POSES={
    'idle': (((15,46),(11,63),(8,80),(7,83)),((21,46),(25,63),(28,80),(31,83))),
    'brace':(((15,46),(10,60),(5,77),(3,81)),((21,46),(27,61),(30,78),(32,81))),
    'stride':(((15,46),(10,62),(7,78),(3,82)),((21,46),(27,58),(23,75),(25,81))),
    'lift':(((15,46),(10,61),(9,78),(7,83)),((21,46),(26,55),(25,67),(29,71))),
    'lunge':(((14,46),(8,62),(5,75),(3,80)),((21,46),(27,56),(27,70),(31,74))),
    'deep':(((14,46),(8,55),(11,66),(7,71)),((21,46),(27,52),(24,63),(28,68))),
    'fold':(((15,46),(10,57),(13,70),(10,75)),((21,46),(27,54),(22,65),(26,70))),
    'extend':(((15,46),(11,62),(9,78),(6,82)),((21,46),(23,63),(25,80),(28,83))),
    'split':(((15,46),(10,59),(5,73),(3,77)),((21,46),(27,60),(30,76),(33,79))),
    'step':(((15,46),(11,60),(13,75),(10,80)),((21,46),(26,61),(29,78),(32,82))),
}

def xy(point):
    return tuple(int(round(float(t))) for t in point)

def segment(draw,a,b,wa,wb,fill):
    a,b=np.array(a,dtype='float64'),np.array(b,dtype='float64')
    d=b-a
    length=max(0.01,float(np.linalg.norm(d)))
    side=np.array((-d[1],d[0]))/length
    poly=[a-side*wa/2,b-side*wb/2,b+side*wb/2,a+side*wa/2]
    draw.polygon([xy(p) for p in poly],fill=fill)

def bead(draw,p,width,fill):
    x,y=p
    radius=(width-1)/2
    draw.ellipse((round(x-radius),round(y-radius),round(x+radius),round(y+radius)),fill=fill)

def limb_leg(points,near):
    hip,knee,heel,toe=np.asarray(points,dtype='float64')
    layer=Image.new('RGBA',SIZE)
    draw=ImageDraw.Draw(layer)
    band=hip+.72*(knee-hip)
    skin=SKIN if near else SKIN_MID
    main=STOCK if near else (35,35,40,255)
    segment(draw,hip,band,5.7,5.0,skin)
    segment(draw,hip+np.array((1.5,0)),band+np.array((1.6,0)),1.4,1.4,SKIN_MID if near else SKIN_SHADOW)
    segment(draw,band,knee,5.1,4.7,main)
    bead(draw,knee,4.4,main)
    segment(draw,knee,heel,4.9,3.6,main)
    bead(draw,heel,4.0,main)
    segment(draw,heel,toe,4.2,3.6,main)
    bead(draw,toe,3.2,main)
    q=knee+.17*(heel-knee)
    l=knee+.82*(heel-knee)
    segment(draw,q+np.array((1.25,0)),l+np.array((.85,0)),1.0,.7,STOCK_SHADOW)
    segment(draw,heel,heel+.65*(toe-heel),1.45,1.35,STOCK_LIGHT if near else STOCK)
    return contour(layer)

def arm_points(wrist,near):
    shoulder=np.asarray((21.0,31.0) if near else (12.0,32.0))
    wrist=np.asarray(wrist,dtype='float64')
    midpoint=(shoulder+wrist)/2
    elbow=midpoint+np.array((3.1 if near else -3.1,1.2 if wrist[1]>=30 else 0))
    elbow=np.clip(elbow,(3.0,12.0),(32.0,51.0))
    return shoulder,elbow,wrist

def limb_arm(wrist,near):
    shoulder,elbow,wrist=arm_points(wrist,near)
    cuff=elbow+.80*(wrist-elbow)
    layer=Image.new('RGBA',SIZE)
    draw=ImageDraw.Draw(layer)
    main=SLEEVE if near else SLEEVE_SHADOW
    segment(draw,shoulder,elbow,5.0,4.0,main)
    bead(draw,elbow,4.0,main)
    segment(draw,elbow,cuff,4.0,3.15,main)
    segment(draw,shoulder+(.9,-.9),elbow+(.7,-.7),1.0,.75,SLEEVE_LIGHT if near else SLEEVE)
    bead(draw,wrist,4.0,SKIN if near else SKIN_MID)
    draw.point(xy(wrist+(0,1)),fill=SKIN_MID if near else SKIN_SHADOW)
    draw.point(xy(wrist+(-1,0)),fill=SKIN_MID)
    return contour(layer)

def character(legs,wrists,head_key,skirt_key,skirt_angle,face_right,body_only=False):
    far,near=legs
    far_wrist,near_wrist=wrists
    cloth,origin=SKIRTS[skirt_key]
    layers=[] if body_only else [limb_leg(far,False),limb_leg(near,True)]
    layers.extend((limb_arm(far_wrist,False),TORSO,stamp(cloth,PIVOT,origin,skirt_angle),
                   HEADS[head_key],limb_arm(near_wrist,True)))
    out=Image.new('RGBA',SIZE)
    for layer in layers:
        out.alpha_composite(layer)
    return ImageOps.mirror(out) if face_right else out

if __name__=='__main__':
    names=['idle','brace','stride','lift','lunge','deep','fold','extend','split','step']
    board=Image.new('RGB',(1200,790),(109,101,109))
    draw=ImageDraw.Draw(board)
    for i,name in enumerate(names):
        arms=((8,40),(28,39)) if i<3 else ((7,28+(i%3)*6),(27,23+(i%4)*5))
        model=character(LEG_POSES[name],arms,list(HEADS)[i%len(HEADS)],list(SKIRTS)[i%3],(i%5-2)*4,i%3!=0)
        model=model.resize((144,344),Image.Resampling.NEAREST)
        x,y=i%5*240+42,i//5*390+20
        board.paste(model,(x,y),model)
        draw.text((x,y+349),name,fill=(255,255,255))
    board.save(root/'rig-test.png')
