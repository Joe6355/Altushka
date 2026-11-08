
"""Native 36x86 continuous limb rig. phase=0 is near heel contact.

The stance occupies 60% of a cycle and advances linearly backwards.
At full amplitude, a planted profile foot moves 18.4 px over .6 cycles,
so matching root travel is 30.67 native px per full gait cycle.
Projected fore/aft ground depth is 3/9.2 of profile ground distance.
All geometry is drawn with opaque nearest-neighbour native pixels.
"""
from math import sin,cos,pi,sqrt
from PIL import Image,ImageDraw
import numpy as np

SIZE=(36,86)
S=4
CAM=3/9.2
VECTORS={
    'down':(0.,1.),'down_right':(2**-.5,2**-.5),
    'right':(1.,0.),'up_right':(2**-.5,-2**-.5),
    'up':(0.,-1.),'up_left':(-2**-.5,-2**-.5),
    'left':(-1.,0.),'down_left':(-2**-.5,2**-.5),
}
INK=(2,2,2,255)
NEAR=(55,55,60,255)
FAR=(34,34,38,255)
SKIN=(255,242,231,255)
SKIN_SHADOW=(247,186,188,255)

def _clamp(v,a=0.,b=1.):return max(a,min(b,float(v)))
def _mix(a,b,t):return np.asarray(a,float)*(1-t)+np.asarray(b,float)*t
def _canvas():return Image.new('RGBA',(SIZE[0]*S,SIZE[1]*S))
def _xy(p):return tuple(int(round((v+.5)*S)) for v in p)
def _native(im):return im.resize(SIZE,Image.Resampling.NEAREST)

def _poly(d,points,color):
    d.polygon([_xy(p) for p in points],fill=color)

def _disc(d,p,width,color):
    x,y=p;r=width/2
    d.ellipse((_xy((x-r,y-r))+_xy((x+r,y+r))),fill=color)

def _segment(d,a,b,wa,wb,color):
    a=np.asarray(a,float);b=np.asarray(b,float)
    v=b-a;norm=float(np.linalg.norm(v))
    if norm<.001:
        _disc(d,a,max(wa,wb),color);return
    n=np.array([-v[1],v[0]])/norm
    _poly(d,(a+n*wa/2,b+n*wb/2,b-n*wb/2,a-n*wa/2),color)
    _disc(d,a,wa,color);_disc(d,b,wb,color)

def _ribbon(d,points,widths,color):
    p=np.asarray(points,float);w=np.asarray(widths,float)
    tangent=np.gradient(p,axis=0)
    length=np.linalg.norm(tangent,axis=1)
    normal=np.stack((-tangent[:,1],tangent[:,0]),1)/np.maximum(length[:,None],.001)
    left=p+normal*w[:,None]/2;right=p-normal*w[:,None]/2
    _poly(d,np.vstack((left,right[::-1])),color)
    _disc(d,p[0],float(w[0]),color);_disc(d,p[-1],float(w[-1]),color)

def _inset(poly,distance=.70):
    p=np.asarray(poly,float);out=[]
    for i in range(len(p)):
        a=p[i-1];b=p[i];c=p[(i+1)%len(p)]
        v=b-a;w=c-b
        nv=np.array([-v[1],v[0]])/max(.001,np.linalg.norm(v))
        nw=np.array([-w[1],w[0]])/max(.001,np.linalg.norm(w))
        s=a+nv*distance;t=b+nw*distance
        mat=np.column_stack((v,-w))
        if abs(np.linalg.det(mat))<.001:out.append(b+(nv+nw)*distance/2)
        else:out.append(s+v*np.linalg.solve(mat,t-s)[0])
    return out

def _hull(points):
    pts=sorted(set((float(p[0]),float(p[1])) for p in points))
    if len(pts)<3:return pts
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[]
    for p in pts:
        while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(pts):
        while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]

def _gait(phase,amount):
    p=(phase/(2*pi))%1
    if p<.6:
        forward=1-2*p/.6;lift=0.
        heel=_clamp((p-.43)/.17)*1.5
        toe=_clamp(1-p/.13)*1.1
    else:
        u=(p-.6)/.4
        forward=-cos(pi*u);lift=6*sin(pi*u)
        heel=0.;toe=.5*sin(pi*u)
    return forward*amount,lift*amount,heel*amount,toe*amount

def _ik(f,v,l1=15.,l2=14.,bend=1):
    # Only a small reach extension, hidden at the hips, is allowed.
    length=sqrt(f*f+v*v)
    if length<.01:return np.array([0.,l1])
    stretch=max(1.,length/(l1+l2-.08))
    stretch=min(stretch,1.065)
    a1=l1*stretch;a2=l2*stretch
    reach=min(length,a1+a2-.02)
    along=(a1*a1-a2*a2+reach*reach)/(2*reach)
    height=sqrt(max(0.,a1*a1-along*along))
    u=np.array([f,v])/length
    perp=np.array([u[1],-u[0]])*bend
    return u*along+perp*height

def _boot_points(ankle,fx,fy,heel,toe):
    ax,ay=ankle
    if abs(fx)<.15:
        # The broad rounded forefoot reads in front/rear view; a profile
        # projection here used to make a rectangular extension of the shin.
        return [(ax+x,ay+y) for x,y in ((-2.5,2.1),(-2.3,.2),(-1.5,-.7),
               (1.5,-.7),(2.3,.2),(2.5,2.1),(1.6,3.6),(-1.6,3.6))]
    points=[]
    for f,l in ((-1.5,-2.1),(-1.5,2.1),(3.8,-1.9),(3.8,1.9)):
        rise=heel if f<0 else toe
        points.append((ax+fx*f+fy*l,ay+3+fy*f*CAM-fx*l*CAM-rise))
    # The short ankle cuff keeps the shin joined to the shoe in all views.
    points.extend(((ax-1.65,ay-.7),(ax+1.65,ay-.7)))
    return _hull(points)

def _boot_height(fx,fy,heel,toe):
    return max(p[1] for p in _boot_points((0,0),fx,fy,heel,toe))

def _draw_boot(d,ankle,fx,fy,heel,toe,near):
    outer=_hull(_boot_points(ankle,fx,fy,heel,toe))
    _poly(d,outer,INK)
    inner=_inset(outer,.70)
    _poly(d,inner,(43,43,48,255) if near else (28,28,33,255))
    # A broad quiet highlight on the upper shoe, not a noisy light rim.
    x,y=ankle
    _segment(d,(x-.4,y+.4),(x+fx*1.3,y+.8+fy*1.3*CAM),.8,.8,
             (55,55,60,255) if near else (36,36,42,255))

def _draw_leg(hip,knee,ankle,view,heel,toe,near):
    fx,fy=VECTORS[view]
    layer=_canvas();d=ImageDraw.Draw(layer)
    # A single soft tapered silhouette has no rigid elbow-shaped knee join.
    hip=np.asarray(hip);knee=np.asarray(knee);ankle=np.asarray(ankle)
    t=np.linspace(0,1,25);control=2*knee-.5*(hip+ankle)
    points=(1-t[:,None])**2*hip+2*t[:,None]*(1-t[:,None])*control+t[:,None]**2*ankle
    outer=np.interp(t,[0,.46,.73,1],[6.4,5.6,5.7,4.55])*(1 if near else .94)
    inner=np.maximum(1,outer-1.5)
    _ribbon(d,points,outer,INK)
    _ribbon(d,points,inner,SKIN if near else SKIN_SHADOW)
    distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    begin=int(np.searchsorted(distance,5.25))
    _ribbon(d,points[begin:],inner[begin:],NEAR if near else FAR)
    # One continuous quiet shadow gives the calf volume without black seams.
    _ribbon(d,points[begin:]+(.7,0),np.linspace(1.15,.7,len(points)-begin),
             (43,43,48,255) if near else (28,28,33,255))
    _draw_boot(d,ankle,fx,fy,heel,toe,near)
    return _native(layer)

def legs(view,phase,amount=1.,bob=0.,dance=0.,sway=0.):
    """Composite far+near legs. dance blends joints into fixed wide feet."""
    fx,fy=VECTORS[view];amount=_clamp(amount);dance=_clamp(dance)
    sign=1 if fx>=0 else -1
    spacing=1+1.8*abs(fy)
    base=85-3*abs(fy)
    pair=[]
    for leg in (1,0):  # far behind near
        near=leg==0;s=1 if near else -1
        hipx=17.5+s*spacing*sign
        hip=np.array((hipx+sway,54+bob+s*.45*abs(fx)),float)
        forward,lift,heel,toe=_gait(phase+(0 if near else pi),amount)
        f=9.2*forward
        height=_boot_height(fx,fy,heel,toe)
        sole=base+fy*f*CAM-lift
        ankle=np.array((hipx+fx*f,sole-height),float)
        v=(base-lift-height)-hip[1]
        k=_ik(f,v)
        # Keep the planted leg almost straight; only the recovering knee
        # bends visibly. Full planar IK made the long legs look zigzagged.
        axis=np.array((f,v));fraction=15/29
        chord=axis*fraction
        swing=_clamp(lift/6)
        k=chord+(k-chord)*(.24+.22*swing)
        knee=np.array((hip[0]+fx*k[0],hip[1]+k[1]+fy*k[0]*CAM))
        if dance:
            dfy=84.
            da=np.array((29. if near else 7.,dfy-_boot_height(fx,fy,0,0)))
            dv=da-hip
            # The knees bank against the hip sway rather than opening outward.
            dk=_ik(float(dv[0]),float(dv[1]),bend=(-1 if sway>=0 else 1))
            chord=dv*(15/29)
            dance_knee=hip+chord+(dk-chord)*.11
            ankle=_mix(ankle,da,dance);knee=_mix(knee,dance_knee,dance)
            heel*=1-dance;toe*=1-dance
        pair.append(_draw_leg(hip,knee,ankle,view,heel,toe,near))
    out=Image.new('RGBA',SIZE)
    for im in pair:out.alpha_composite(im)
    return out

def _arm_joint(view,phase,amount,bob,sway,near):
    fx,fy=VECTORS[view];sign=1 if fx>=0 else -1
    s=1 if near else -1
    spacing=1.65+3.6*abs(fy)
    shoulder=np.array((17.5+s*spacing*sign+sway,32+bob+s*.4*abs(fx)))
    q,lift,heel,toe=_gait(phase+(0 if near else pi),amount)
    swing=-q*7.3
    wrist=np.array((shoulder[0]+fx*swing,49+bob+fy*swing*CAM-.35*amount))
    # Elbow travels through a smaller arc with a mild relaxed rearward bend.
    elbow=np.array((shoulder[0]+fx*(swing*.56-.45*amount),
                    40.5+bob+fy*swing*.42*CAM))
    return shoulder,elbow,wrist

def _draw_arm(shoulder,elbow,wrist,near):
    layer=_canvas();d=ImageDraw.Draw(layer)
    cuff=_mix(elbow,wrist,.79)
    _segment(d,shoulder,elbow,5.35 if near else 4.8,4.8 if near else 4.4,INK)
    _segment(d,elbow,cuff,4.6 if near else 4.25,3.75 if near else 3.4,INK)
    _segment(d,shoulder,elbow,3.7 if near else 3.15,3.15 if near else 2.75,
             (36,36,42,255) if near else (24,24,29,255))
    _segment(d,elbow,cuff,3.0 if near else 2.7,2.1 if near else 1.9,
             (43,43,48,255) if near else (24,24,29,255))
    off=np.array([-.6,0])
    _segment(d,shoulder+off,elbow+off,.8,.65,
             (55,55,61,255) if near else (36,36,42,255))
    _segment(d,elbow+off,cuff+off,.65,.55,
             (55,55,61,255) if near else (36,36,42,255))
    _segment(d,cuff,wrist,2.1,2.4,SKIN if near else SKIN_SHADOW)
    # A tiny mitten-shaped palm: a clean silhouette on the original grid.
    x,y=wrist
    d.rectangle(_xy((x-1.55,y-1.05))+_xy((x+1.55,y+1.6)),fill=INK)
    d.rectangle(_xy((x-.95,y-.55))+_xy((x+.95,y+1.05)),
                fill=SKIN if near else SKIN_SHADOW)
    d.point(_xy((x+.8,y+.9)),fill=(215,124,128,255))
    return _native(layer)

def arms(view,phase,amount=1.,bob=0.,dance=0.,sway=0.):
    """Return (far, near) sleeve/hand layers; dance blends joint targets."""
    amount=_clamp(amount);dance=_clamp(dance)
    layers=[]
    for near in (False,True):
        shoulder,elbow,wrist=_arm_joint(view,phase,amount,bob,sway,near)
        if dance:
            ds=np.array((23. if near else 12.,32.))+[sway,bob]
            de=np.array((30. if near else 7.,36. if near else 41.))+[sway,bob]
            dw=np.array((28. if near else 11.,42. if near else 37.))+[sway,bob]
            shoulder=_mix(shoulder,ds,dance)
            elbow=_mix(elbow,de,dance);wrist=_mix(wrist,dw,dance)
        layers.append(_draw_arm(shoulder,elbow,wrist,near))
    return tuple(layers)

if __name__=='__main__':
    # Geometry checks are meaningful here: clipping would hide the foot plant.
    for view in VECTORS:
        for amount in (0.,.5,1.):
            for phase in np.linspace(0,2*pi,65):
                for bob in (-1.,0.,1.):
                    im=legs(view,float(phase),amount,bob)
                    assert im.size==SIZE and im.getbbox()
                    a=np.asarray(im)
                    assert set(np.unique(a[:,:,3]))<={0,255}
                    assert not a[:,0,3].any() and not a[:,-1,3].any(),(view,phase,bob)
    print('8-direction leg rig: native RGBA, no horizontal clipping at all sampled phases.')
