
import numpy as np
from PIL import Image

def pixel_morph(a,b,t):
    """Move opaque pixel spans into one intermediate silhouette."""
    if t<=0:return a.copy()
    if t>=1:return b.copy()
    aa=np.asarray(a);bb=np.asarray(b);out=np.zeros_like(aa)
    for y in range(aa.shape[0]):
        ax=np.flatnonzero(aa[y,:,3]);bx=np.flatnonzero(bb[y,:,3])
        na,nb=len(ax),len(bx)
        count=round(na*(1-t)+nb*t)
        if not count:continue
        q=(np.arange(count)+.5)/count
        if na:
            ai=np.clip((q*na).astype(int),0,na-1)
            xa=ax[ai].astype(float);ca=aa[y,ax[ai],:3].astype(float)
            ar=np.r_[0,np.cumsum(np.diff(ax)>1)][ai]
        if nb:
            bi=np.clip((q*nb).astype(int),0,nb-1)
            xb=bx[bi].astype(float);cb=bb[y,bx[bi],:3].astype(float)
            br=np.r_[0,np.cumsum(np.diff(bx)>1)][bi]
        if not na:xa,ca,ar=xb,cb,br
        if not nb:xb,cb,br=xa,ca,ar
        dest=np.rint(xa*(1-t)+xb*t).astype(int)
        if y<34:
            rgb=np.rint(ca if t<.5 else cb).clip(0,255).astype(np.uint8)
        else:
            rgb=np.rint(ca*(1-t)+cb*t).clip(0,255).astype(np.uint8)
        sums=np.zeros((aa.shape[1],3),float);weights=np.zeros(aa.shape[1],float)
        np.add.at(sums,dest,rgb);np.add.at(weights,dest,1)
        valid=weights>0
        out[y,valid,:3]=np.rint(sums[valid]/weights[valid,None]).astype(np.uint8)
        out[y,valid,3]=255
        # Rasterize the area between neighbouring samples of the same
        # silhouette span. Resampling must not leave striped one-pixel holes.
        for i in range(count-1):
            left,right=int(dest[i]),int(dest[i+1])
            if right-left>1 and ar[i]==ar[i+1] and br[i]==br[i+1]:
                for x in range(left+1,right):
                    u=(x-left)/(right-left)
                    out[y,x,:3]=np.rint(rgb[i]*(1-u)+rgb[i+1]*u).astype(np.uint8)
                    out[y,x,3]=255
    # A single face texture is used through each half-turn; eye colours
    # are never mixed into multiple competing sets of facial features.
    return Image.fromarray(out)
