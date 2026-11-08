from pathlib import Path
from ctypes import *
from PIL import Image, ImageDraw
import sys
import numpy as np

from decode import (DLLS, codec, avutil, ptr, bind, check, codec_alloc, codec_open,
    packet_alloc, packet_unref, frame_alloc, send_packet, recv_frame, sws_get, sws_scale)
from encode import fmt, Stream, FormatContext, OutputPacket, VideoParams, VideoFrame, params_to_ctx

class InputContext(Structure):
    _fields_ = FormatContext._fields_ + [
        ("ctx_flags", c_int), ("nb_streams", c_uint), ("streams", POINTER(POINTER(Stream)))
    ]

open_input = bind(fmt, "avformat_open_input", c_int, POINTER(POINTER(InputContext)), c_char_p, ptr, ptr)
find_info = bind(fmt, "avformat_find_stream_info", c_int, POINTER(InputContext), ptr)
find_best = bind(fmt, "av_find_best_stream", c_int, POINTER(InputContext), c_int,c_int,c_int,POINTER(ptr),c_int)
read_frame = bind(fmt, "av_read_frame", c_int, POINTER(InputContext), ptr)

def decode_reference(path,max_side=None,raw=False):
    demux = POINTER(InputContext)()
    check(open_input(byref(demux),str(path).encode("utf8"),None,None))
    check(find_info(demux,None))
    decoder = ptr()
    stream_index = check(find_best(demux,0,-1,-1,byref(decoder),0))
    stream = demux.contents.streams[stream_index].contents
    params = cast(stream.codecpar,POINTER(VideoParams))
    p = params.contents
    print("Stream", stream_index, "of", demux.contents.nb_streams,
          "codec", p.codec_id, "resolution", (p.width,p.height),
          "framerate", (p.framerate.num,p.framerate.den),
          "timebase", (stream.time_base.num,stream.time_base.den), flush=True)
    ctx = codec_alloc(decoder)
    check(params_to_ctx(ctx,params))
    check(codec_open(ctx,decoder,None))
    pkt = packet_alloc()
    packet = cast(pkt,POINTER(OutputPacket)).contents
    frame = frame_alloc()
    attrs = cast(frame,POINTER(VideoFrame)).contents
    scale_ctx = None

    def drain():
        nonlocal scale_ctx
        while True:
            status = recv_frame(ctx,frame)
            if status in (-11,-541478725):
                break
            check(status)
            w,h = attrs.width,attrs.height
            if raw:
                assert attrs.format==0
                sizes=((h,w),(h//2,w//2),(h//2,w//2))
                planes=[]
                for i,(rows,cols) in enumerate(sizes):
                    stride=attrs.linesize[i]
                    plane=np.frombuffer(string_at(attrs.data[i],rows*stride),dtype='uint8')
                    planes.append(plane.reshape(rows,stride)[:,:cols].copy())
                ts=attrs.pts*stream.time_base.num/stream.time_base.den
                yield ts,planes
                continue
            ratio = min(1,max_side/max(w,h)) if max_side else 1
            out_w,out_h = round(w*ratio),round(h*ratio)
            if scale_ctx is None:
                scale_ctx = sws_get(w,h,attrs.format,out_w,out_h,2,0x10,None,None,None)
                assert scale_ctx
            rgb = create_string_buffer(out_w*out_h*3+128)
            out = (ptr*4)(addressof(rgb))
            lines = (c_int*4)(out_w*3)
            assert sws_scale(scale_ctx,attrs.data,attrs.linesize,0,h,out,lines) == out_h
            ts = attrs.pts * stream.time_base.num / stream.time_base.den
            yield ts,Image.frombytes("RGB",(out_w,out_h),rgb.raw[:out_w*out_h*3])
    while True:
        status = read_frame(demux,pkt)
        if status == -541478725:
            break
        check(status)
        if packet.stream_index == stream_index:
            check(send_packet(ctx,pkt))
            yield from drain()
        packet_unref(pkt)
    check(send_packet(ctx,None))
    yield from drain()

def sheet(frames,samples,name,root,cell=(205,228),cols=5):
    w,h = cell
    board = Image.new("RGB",(w*cols,h*((len(samples)+cols-1)//cols)),(24,24,28))
    draw = ImageDraw.Draw(board)
    for n,i in enumerate(samples):
        time,img = frames[i]
        x,y = n%cols*w,n//cols*h
        thumb = img.copy()
        thumb.thumbnail((w-5,h-21),Image.Resampling.NEAREST)
        board.paste(thumb,(x+(w-thumb.width)//2,y))
        draw.text((x+7,y+h-17),f"{i} | {time:.3f}s",fill=(230,230,231))
    board.save(root/name)

if __name__ == '__main__':
    root = Path(__file__).parent
    frames = list(decode_reference(Path(sys.argv[1]),500))
    print("Decoded",len(frames),"first and last PTS",(frames[0][0],frames[-1][0]), flush=True)
    print("Initial timings", [round(t,4) for t,_ in frames[:24]])
    samples = list(dict.fromkeys(round(i*(len(frames)-1)/23) for i in range(24)))
    sheet(frames,samples,'reference.png',root)
    for i,(t,img) in enumerate(frames):
        img.save(root/f'ref_{i:04}.png',compress_level=1)
