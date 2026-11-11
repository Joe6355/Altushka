"""Retarget a public walking reference to Alisa's existing native proportions.

Only joint coordinates are calculated here. All pixel editing and rendering is
performed by build.lua in Aseprite. The resulting pose plan is versioned so the
native asset can be rebuilt without downloading or executing website code.
"""
from pathlib import Path
import json
import math
import re
import numpy as np

HERE = Path(__file__).resolve().parent
text = (HERE / 'reference/Walker.js').read_text('utf-8')
def coefficients(name):
    raw = re.search(r'this\.' + name + r'\s*=\s*new Array\(([^;]+)\);', text).group(1)
    return np.array([float(v.strip()) for v in raw.split(',')])
model = coefficients(r'meanwalker\[0\]') + coefficients('genderaxis')
def sample(phase):
    weights = (1, np.sin(phase), np.cos(phase), np.sin(2*phase), np.cos(2*phase))
    return sum(model[k*46:k*46+45]*w for k,w in enumerate(weights)).reshape(3,15).T

poses = []
GROUND_PROJECTION = .026
GROUND_DEPTH = .0125
HEIGHT_SCALE = .029
for frame in range(20):
    phase = frame / 20 * 2*math.pi
    p = sample(phase)
    sway = 1.4*math.sin(phase-.15)
    bob = -(p[8,2]-1011)*.033
    legs = []
    for hip,knee,ankle,shift in ((12,13,14,10),(9,10,11,0)):
        step = (frame+shift)%20
        # Grounded ankle travel is linear: the root cancels it exactly in the
        # moving preview. The swing still follows the measured knee/ankle arc.
        forward = 285-65*step if step<=9 else p[ankle,0]
        ankle_z = 116 if step<=8 else p[ankle,2]
        def project(joint, amount):
            f,l,z = p[joint]
            return [18.3 + l*.035-f*GROUND_PROJECTION+sway*amount,
                    54-(z-910)*HEIGHT_SCALE+f*GROUND_DEPTH]
        h = project(hip,1)
        k = project(knee,.35)
        a = [18.3+p[ankle,1]*.035-forward*GROUND_PROJECTION,
             54-(ankle_z-910)*HEIGHT_SCALE+forward*GROUND_DEPTH]
        # Shoe lifts at heel contact and rolls at toe-off; never a hinged shin.
        roll = {0:-.18,1:-.08,7:.06,8:.17,9:.28,10:.33,11:.18,18:-.16,19:-.22}.get(step,0)
        legs.append(dict(hip=h,knee=k,ankle=a,roll=roll,step=step))
    poses.append(dict(sway=sway,bob=bob,phase=phase,legs=legs))
document = dict(nativeSize=[36,86], frameDurationMs=60, pivot=[18,85],
                reference='https://www.biomotionlab.ca/Demos/bmlwalker/',
                note='Retargeted joint plan; original Alisa textures, not reference imagery.',
                rootVelocity=[-65*GROUND_PROJECTION/.06,65*GROUND_DEPTH/.06], poses=poses)
(HERE/'poses.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n','utf-8')
print('Saved 20 retargeted poses; root velocity',document['rootVelocity'])
