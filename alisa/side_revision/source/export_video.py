"""Convert the Aseprite-exported movement GIF into the MP4 review copy."""
from pathlib import Path
import sys
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
sys.path.insert(0,str(HERE.parents[2]/'alisa/rear_key_redraw/source'))
from encode import encode
from refdecode import decode_reference

M=np.array([[65.481,128.553,24.966],[-37.797,-74.203,112.0],
            [112.0,-93.786,-18.214]],np.float32)/255


def frame_planes(number):
    with Image.open(OUT/'Alisa_side_movement.gif') as gif:
        gif.seek(number)
        assert gif.info['duration']==80 and gif.size==(1280,960)
        rgb=np.asarray(gif.convert('RGB')).astype(np.float32)
    a=np.clip(np.rint(rgb@M.T+[16,128,128]),0,255).astype(np.uint8)
    chroma=[np.rint(a[:,:,i].reshape(480,2,640,2).mean((1,3))).astype(np.uint8) for i in (1,2)]
    return a[:,:,0],*chroma


def main():
    with Image.open(OUT/'Alisa_side_movement.gif') as gif:assert gif.n_frames==60
    path=OUT/'Alisa_side_revision.mp4'
    encode((frame_planes(i) for i in range(60)),path,1280,960,100,durations=[8]*60)
    count=0;error=0
    for n,(timestamp,actual) in enumerate(decode_reference(path,raw=True)):
        assert abs(timestamp-n*.08)<1e-6 and actual[0].shape==(960,1280)
        if n%6==0:
            for expected,plane in zip(frame_planes(n),actual):
                error=max(error,int(np.abs(expected.astype(np.int16)-plane.astype(np.int16)).max()))
        count+=1
    assert count==60 and error<=6,(count,error)
    print(f'MP4 verified: 60 frames, 4.8 seconds, timestamps and sampled pixels; maximum YUV error {error}.',flush=True)


if __name__=='__main__':main()
