from ctypes import *
import numpy as np
from decode import DLLS, codec, avutil, ptr, bind, check, codec_alloc, codec_open, find_encoder, Frame, frame_alloc, Packet, packet_alloc

fmt = CDLL(str(DLLS / "avformat-61.dll"))

class Rational(Structure):
    _fields_ = [("num", c_int), ("den", c_int)]

class VideoFrame(Structure):
    _fields_ = Frame._fields_ + [
        ("key_frame", c_int), ("pict_type", c_int), ("sample_aspect_ratio", Rational),
        ("pts", c_int64), ("pkt_dts", c_int64), ("time_base", Rational)
    ]

class OutputPacket(Structure):
    _fields_ = Packet._fields_ + [
        ("stream_index", c_int), ("flags", c_int), ("side_data", ptr),
        ("side_data_elems", c_int), ("duration", c_int64)
    ]

class VideoParams(Structure):
    _fields_ = [
        ("codec_type", c_int), ("codec_id", c_int), ("codec_tag", c_uint),
        ("extradata", ptr), ("extradata_size", c_int), ("coded_side_data", ptr),
        ("nb_coded_side_data", c_int), ("format", c_int), ("bit_rate", c_int64),
        ("bits_per_coded_sample", c_int), ("bits_per_raw_sample", c_int),
        ("profile", c_int), ("level", c_int), ("width", c_int), ("height", c_int),
        ("sample_aspect_ratio", Rational), ("framerate", Rational)
    ]

class Stream(Structure):
    _fields_ = [
        ("av_class", ptr), ("index", c_int), ("id", c_int), ("codecpar", ptr),
        ("priv_data", ptr), ("time_base", Rational)
    ]

class FormatContext(Structure):
    _fields_ = [("av_class", ptr), ("iformat", ptr), ("oformat", ptr),
                ("priv_data", ptr), ("pb", ptr)]

dict_set = bind(avutil, "av_dict_set", c_int, POINTER(ptr), c_char_p, c_char_p, c_int)
opt_set = bind(avutil, "av_opt_set", c_int, ptr, c_char_p, c_char_p, c_int)
params_alloc = bind(codec, "avcodec_parameters_alloc", POINTER(VideoParams))
params_free = bind(codec, "avcodec_parameters_free", None, POINTER(POINTER(VideoParams)))
params_to_ctx = bind(codec, "avcodec_parameters_to_context", c_int, ptr, POINTER(VideoParams))
params_from_ctx = bind(codec, "avcodec_parameters_from_context", c_int, ptr, ptr)
frame_get_buffer = bind(avutil, "av_frame_get_buffer", c_int, ptr, c_int)
frame_make_writable = bind(avutil, "av_frame_make_writable", c_int, ptr)
send_frame = bind(codec, "avcodec_send_frame", c_int, ptr, ptr)
recv_packet = bind(codec, "avcodec_receive_packet", c_int, ptr, ptr)
ts_rescale = bind(codec, "av_packet_rescale_ts", None, ptr, Rational, Rational)
alloc_format = bind(fmt, "avformat_alloc_output_context2", c_int, POINTER(POINTER(FormatContext)), ptr, c_char_p, c_char_p)
new_stream = bind(fmt, "avformat_new_stream", POINTER(Stream), POINTER(FormatContext), ptr)
avio_open = bind(fmt, "avio_open", c_int, POINTER(ptr), c_char_p, c_int)
avio_close = bind(fmt, "avio_closep", c_int, POINTER(ptr))
write_header = bind(fmt, "avformat_write_header", c_int, POINTER(FormatContext), POINTER(ptr))
write_packet = bind(fmt, "av_interleaved_write_frame", c_int, POINTER(FormatContext), ptr)
write_trailer = bind(fmt, "av_write_trailer", c_int, POINTER(FormatContext))

def settings(**pairs):
    d = ptr()
    for name,value in pairs.items():
        check(dict_set(byref(d), name.encode(), value.encode(), 0))
    return d

def encode(frames, path, w, h, fps, durations=None):
    encoder = find_encoder(b"libx264")
    assert encoder
    ctx = codec_alloc(encoder)
    params = params_alloc()
    p = params.contents
    p.codec_type = 0
    p.codec_id = 27
    p.format = 0
    p.width, p.height = w, h
    p.sample_aspect_ratio = Rational(1, 1)
    p.framerate = Rational(fps if durations is None else 24, 1)
    check(params_to_ctx(ctx, params))
    params_free(byref(params))
    tb = Rational(1, fps)
    check(opt_set(ctx, b"time_base", f"1/{fps}".encode(), 0))
    check(opt_set(ctx, b"flags", b"+global_header", 0))
    opt = settings(preset="medium", qp="1", profile="high", **{"x264-params":"bframes=0:keyint=40:scenecut=0:no-deblock=1"})
    check(codec_open(ctx, encoder, byref(opt)))
    print("Encoder opened", flush=True)

    dst = str(path).encode("utf-8")
    muxer = POINTER(FormatContext)()
    check(alloc_format(byref(muxer), None, b"mp4", dst))
    stream = new_stream(muxer, None)
    s = stream.contents
    assert s.codecpar
    s.time_base = tb
    check(params_from_ctx(s.codecpar, ctx))
    pb = ptr()
    check(avio_open(byref(pb), dst, 2))
    muxer.contents.pb = pb
    opt = settings(movflags="+faststart", video_track_timescale="100")
    check(write_header(muxer, byref(opt)))
    print("Muxer opened with timebase", s.time_base.num, s.time_base.den, flush=True)

    frame = cast(frame_alloc(), POINTER(VideoFrame))
    f = frame.contents
    f.width, f.height, f.format = w, h, 0
    f.sample_aspect_ratio = Rational(1, 1)
    f.time_base = tb
    check(frame_get_buffer(frame, 32))
    packet = cast(packet_alloc(), POINTER(OutputPacket))
    samples = []
    starts = None if durations is None else np.cumsum([0,*durations[:-1]])
    def drain():
        while True:
            status = recv_packet(ctx, packet)
            if status in (-11, -541478725):
                return
            check(status)
            p = packet.contents
            sample_index = len(samples)
            expected = sample_index if starts is None else int(starts[sample_index])
            assert p.pts == p.dts == expected, (p.pts, p.dts, expected)
            samples.append((p.pts, p.size))
            p.duration = 1 if durations is None else int(durations[sample_index])
            p.stream_index = s.index
            ts_rescale(packet, tb, s.time_base)
            check(write_packet(muxer, packet))
    for n, planes in enumerate(frames):
        check(frame_make_writable(frame))
        for i, plane in enumerate(planes):
            height, width = plane.shape
            addr = (c_uint8 * (f.linesize[i] * height)).from_address(f.data[i])
            np.ctypeslib.as_array(addr).reshape(height, f.linesize[i])[:, :width] = plane
        f.pts = n if starts is None else int(starts[n])
        check(send_frame(ctx, frame))
        drain()
    check(send_frame(ctx, None))
    drain()
    check(write_trailer(muxer))
    check(avio_close(byref(pb)))
    print("Wrote", len(samples), "packets,", sum(size for pts,size in samples), "bytes of video data", flush=True)
