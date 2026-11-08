"""Recreate the native base from the preserved generated profile reference."""
from pathlib import Path
from PIL import Image
import numpy as np

R=Path(__file__).resolve().parent
PALETTE=[
 (2,2,2),(24,24,29),(34,34,38),(43,43,48),(55,55,60),
 (70,70,78),(139,139,150),(164,164,174),(190,190,200),
 (213,213,223),(232,232,239),(244,244,248),(255,255,255),
 (255,242,231),(247,186,188),(229,145,158),(212,112,135),
 (55,183,226),(139,232,245),(39,92,128),
]
im=Image.open(R/'Profile_reference_generated.png').convert('RGBA')
a=np.asarray(im).copy();a[a[:,:,3]<128]=0;a[a[:,:,3]>=128,3]=255
im=Image.fromarray(a);im=im.crop(im.getbbox())
w=round(im.width*86/im.height);im=im.resize((w,86),Image.Resampling.NEAREST)
native=Image.new('RGBA',(36,86));native.paste(im,((36-w)//2,0))
a=np.asarray(native).copy();colors=np.array(PALETTE,np.int16)
delta=a[:,:,:3,None].astype(np.int32)-colors.T[None,None,:,:]
index=(delta*delta).sum(2).argmin(2)
a[:,:,:3]=colors[index].astype(np.uint8);a[a[:,:,3]==0]=0
Image.fromarray(a).save(R/'Profile_native.png')
print('Native profile36x86 exported in20-color palette.')
