
"""Hand-authored lower-body transition cels for the accepted walk.

The caller supplies the existing cycle module on sys.path. No IK, image morph
or source-image warp is used. START/STOP include both exact endpoint poses.
"""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import cycle

SIZE=(36,86)
IDLE_UPPER_PHASE=4
START_UPPER_PHASES=(4,3,2,1,0)
STOP_UPPER_PHASES=(0,1,2,3,4)
START_END_WALK_PHASE=0
STOP_BEGIN_WALK_PHASE=0
START_MS=(100,100,100,100,100)
STOP_MS=(100,100,100,100,100)
# An anticipation/closing step in place; root motion begins after contact0.
START_ROOT_OFFSETS=((0,0),)*5
STOP_ROOT_OFFSETS=((0,0),)*5

def _paint(points,shade,far=False):
    im=Image.new('RGBA',SIZE)
    d=ImageDraw.Draw(im)
    d.polygon(points,fill=(43,43,48,255) if far else (55,55,60,255),outline=(2,2,2,255))
    sh=Image.new('RGBA',SIZE)
    ImageDraw.Draw(sh).polygon(shade,fill=(28,28,33,255) if far else (43,43,48,255))
    a=np.asarray(sh).copy();base=np.asarray(im)
    a[base[:,:,3]==0]=0
    im.alpha_composite(Image.fromarray(a))
    a=np.asarray(im).copy();yy,_=np.indices((86,36))
    skin=(a[:,:,3]>0)&(yy<60)&(a[:,:,:3].max(2)>3)
    a[skin,:3]=(247,186,188) if far else (255,242,231)
    sole=max(y for x,y in points)
    bottom=(a[:,:,3]>0)&(yy>=sole-1)&(a[:,:,:3].max(2)>3)
    a[bottom,:3]=(24,24,29) if far else (34,34,38)
    return Image.fromarray(a)

def _hips():
    im=Image.new('RGBA',SIZE)
    ImageDraw.Draw(im).polygon(
        [(12,47),(23,47),(25,51),(24,57),(20,60),(15,59),(12,55)],
        fill=(247,186,188,255))
    return im

def make_lower(near_points,far_points,near_shade,far_shade):
    im=_paint(far_points,far_shade,True)
    im.alpha_composite(_hips())
    im.alpha_composite(_paint(near_points,near_shade,False))
    return im

def split_lower(full,upper_phase):
    a=np.asarray(full).copy()
    a[np.asarray(cycle.upper(upper_phase))[:,:,3]>0]=0
    return Image.fromarray(a)

def walk_lower(phase):
    phase%=10
    return split_lower(cycle.FRAMES[phase],phase)

def compose(lower,upper_phase):
    im=lower.copy();im.alpha_composite(cycle.upper(upper_phase));return im

# Exact original source pose4, stabilized with the same +3px as its upper.
_original_idle=Image.new('RGBA',SIZE)
_original_idle.paste(cycle.source(4),(cycle.NECK_DX[4],0))
IDLE_LOWER=split_lower(_original_idle,4)

# The leading foot lifts2px, reaches, and plants before the trailing foot
# leaves the original stance. At least one sole remains at y85 throughout.
N1=[(12,55),(19,56),(19,63),(18,69),(15,76),(13,79),(13,83),
    (6,83),(5,82),(5,81),(8,79),(9,75),(10,68),(9,62)]
N2=[(15,55),(21,56),(20,63),(18,69),(13,78),(12,80),(12,84),
    (5,84),(4,83),(4,82),(7,80),(8,76),(11,68),(12,61)]
NS1=[(17,59),(19,60),(18,68),(15,77),(13,80),(11,80),(14,68),(14,62)]
NS2=[(19,59),(21,59),(20,64),(18,70),(12,81),(10,81),(15,69),(16,62)]
F1=[(20,55),(27,56),(27,63),(30,70),(32,77),(33,81),(34,85),
    (27,85),(26,84),(26,83),(28,81),(27,76),(24,69),(21,63)]
F2=[(18,55),(24,56),(25,63),(29,70),(31,77),(32,81),(34,85),
    (27,85),(26,84),(26,83),(28,81),(27,76),(23,69),(19,62)]
F3=[(15,54),(21,55),(25,63),(28,70),(30,76),(31,80),(29,82),
    (24,82),(23,81),(23,80),(26,78),(24,73),(21,68),(17,61)]
FS1=[(25,59),(27,60),(28,66),(31,74),(33,81),(31,81),(28,73),(25,66)]
FS2=[(22,59),(24,59),(26,65),(30,72),(32,81),(30,81),(27,73),(23,67)]
FS3=[(19,57),(21,57),(25,64),(28,71),(30,79),(28,80),(26,72),(22,67)]

_mid1=make_lower(N1,F1,NS1,FS1)
_mid2=make_lower(N2,F2,NS2,FS2)
_mid3=_paint(F3,FS3,True)
_mid3.alpha_composite(_hips())
_mid3.alpha_composite(cycle.leg(0,False))
START_LOWER=(IDLE_LOWER,_mid1,_mid2,_mid3,walk_lower(0))
STOP_LOWER=tuple(reversed(START_LOWER))

def validate():
    assert compose(IDLE_LOWER,4).tobytes()==_original_idle.tobytes()
    assert compose(START_LOWER[-1],0).tobytes()==cycle.FRAMES[0].tobytes()
    assert compose(STOP_LOWER[0],0).tobytes()==cycle.FRAMES[0].tobytes()
    assert compose(STOP_LOWER[-1],4).tobytes()==_original_idle.tobytes()
    for seq in (START_LOWER,STOP_LOWER):
        for im in seq:
            assert im.size==SIZE
            a=np.asarray(im)
            assert set(np.unique(a[:,:,3]))<={0,255}
            assert a[85,:,3].any()
    return True

validate()

if __name__=='__main__':
    root=Path(__file__).resolve().parent
    board=Image.new('RGBA',(36*5,86*2),(105,99,112,255))
    for row,(seq,uppers) in enumerate(((START_LOWER,START_UPPER_PHASES),(STOP_LOWER,STOP_UPPER_PHASES))):
        for n,(lower,phase) in enumerate(zip(seq,uppers)):
            board.alpha_composite(compose(lower,phase),(n*36,row*86))
    board.resize((1080,1032),Image.Resampling.NEAREST).convert('RGB').save(root/'start_stop_review.png')
    print('Exact idle/source4 and walk/contact0 endpoints verified; five start and five stop cels.')
