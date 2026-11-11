"""Retarget a saved numeric walking reference to the original 36x86 grid.

This writes joint coordinates, not artwork. Aseprite draws the positional guide;
the public reference JavaScript is parsed for numbers and never executed.
"""
from pathlib import Path
import hashlib,json,math,re
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
raw=(ROOT/'alisa/confident_walk/source/reference/Walker.js').read_text('utf-8')
def coefficients(name):
    s=re.search(r'this\.'+name+r'\s*=\s*new Array\(([^;]+)\);',raw).group(1)
    return np.array([float(v.strip()) for v in s.split(',')])
model=coefficients(r'meanwalker\[0\]')+coefficients('genderaxis')
def sample(t):
    ws=(1,np.sin(t),np.cos(t),np.sin(2*t),np.cos(2*t))
    return sum(model[k*46:k*46+45]*w for k,w in enumerate(ws)).reshape(3,15).T

result={}
for name,yaw in [('s',0),('n',180),('sw',45),('nw',135)]:
    angle=math.radians(yaw);co,si=math.cos(angle),math.sin(angle)
    frames=[]
    for index in range(8):
        t=index*math.tau/8;p=sample(t)
        sway=1.1*math.sin(t-.15);legs=[]
        for h,k,a,sign in [(9,10,11,1),(12,13,14,-1)]:
            points=[]
            for joint in [h,k,a]:
                f,l,z=p[joint]
                if joint==a:
                    lateral=sign*(3.7+(abs(l)-50)*.02)
                    z=min(z,215)
                else:lateral=l*.035+sway*(1 if joint==h else .3)
                x=18+lateral*co-f*.032*si
                y=54-(z-910)*.029+f*.012*co
                points.append([round(x,3),round(y,3)])
            legs.append(points)
        frames.append(dict(legs=legs,bob=round(-(p[8,2]-1011)*.033,3)))
    frames.append(dict(legs=[[[21.5,54],[21,68],[22,81]],[[14.5,54],[15,68],[14,81]]],bob=0))
    result[name]=frames
(HERE/'pose_plan.json').write_text(json.dumps(result,indent=2)+'\n','utf-8')

approved=[
 'recolor/blue_eyes/Altushka_blue.aseprite',
 'recolor/blue_eyes/Altushka_blue_atlas.png',
 'alisa/side_revision/Alisa_side_revision.aseprite',
 'alisa/side_revision/Alisa_side_revision_atlas.png',
 'unity/Alisa2D/Assets/Alisa/Animations/Clips/SideRevision__walk_side_right.anim',
 'unity/Alisa2D/Assets/Alisa/Animations/Clips/Side__idle_side_right.anim',
 'unity/Alisa2D/Assets/Alisa/Animations/Clips/Front__dance_original.anim']
checks={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in approved}
(HERE/'approved_hashes.json').write_text(json.dumps(checks,indent=2)+'\n','utf-8')
print('Prepared four nine-pose guides; recorded approved dance and A/D hashes.')
