"""Read public BML numeric coefficients for local gait analysis; no website code is executed."""
from pathlib import Path
import re
import json
import numpy as np

HERE=Path(__file__).resolve().parent
text=(HERE/'reference/Walker.js').read_text('utf-8')
def coefficients(name):
    raw=re.search(r'this\.'+name+r'\s*=\s*new Array\(([^;]+)\);',text).group(1)
    return np.array([float(v.strip()) for v in raw.split(',')])
base=coefficients(r'meanwalker\[0\]')
gender=coefficients('genderaxis')
n=15; stride=46
model=base+gender
def sample(phase):
    weights=(1,np.sin(phase),np.cos(phase),np.sin(2*phase),np.cos(2*phase))
    p=sum(model[k*stride:k*stride+45]*w for k,w in enumerate(weights))
    return p.reshape(3,n).T
print('BML numeric analysis:',len(base),'coefficients; period',round(model[45]/120,3),'seconds')
for i in range(20):
    p=sample(i/20*2*np.pi)
    print(i,'pelvis',p[8].round(1).tolist(),'hip tilt',round(p[9,2]-p[12,2],1),
          'right ankle',p[11].round(1).tolist(),'left ankle',p[14].round(1).tolist())

