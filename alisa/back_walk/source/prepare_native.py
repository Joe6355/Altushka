"""Convert the preserved reference drawings into the existing native palette."""
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

def convert(name):
 im=Image.open(R/f'{name}_reference_generated.png').convert('RGBA')
 a=np.asarray(im).copy();a[a[:,:,3]<128]=0;a[a[:,:,3]>=128,3]=255
 im=Image.fromarray(a);box=im.getbbox();im=im.crop(box)
 w=round(im.width*86/im.height);im=im.resize((w,86),Image.Resampling.NEAREST)
 native=Image.new('RGBA',(36,86));native.paste(im,((36-w)//2,0))
 a=np.asarray(native).copy();colors=np.array(PALETTE,np.int16)
 delta=a[:,:,:3,None].astype(np.int32)-colors.T[None,None,:,:]
 index=(delta*delta).sum(2).argmin(2)
 a[:,:,:3]=colors[index].astype(np.uint8);a[a[:,:,3]==0]=0
 im=Image.fromarray(a);im.save(R/f'{name}_native.png')
 print(name,'bbox',box,'native active',im.getbbox())
 return im

if __name__=='__main__':
 ims=[convert(name) for name in ('Back','Back_diagonal')]
 bg=Image.new('RGBA',(108,96),(105,99,112,255))
 side=Image.open(R.parents[1]/'side_walk/Alisa_side_idle.png').convert('RGBA')
 for i,im in enumerate((side,*ims)):bg.alpha_composite(im,(36*i,5))
 bg.resize((864,768),Image.Resampling.NEAREST).save(R/'native_review.png')
