from pathlib import Path
from struct import unpack_from
from ctypes import *
import os, sys

DLLS = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.shared")
dll_dirs = [os.add_dll_directory(str(DLLS)), os.add_dll_directory(str(DLLS.parent))]
codec = CDLL(str(DLLS / "avcodec-61.dll"))
avutil = CDLL(str(DLLS / "avutil-59.dll"))
sws = CDLL(str(DLLS / "swscale-8.dll"))

class Packet(Structure):
    _fields_ = [("buf", c_void_p), ("pts", c_int64), ("dts", c_int64),
                ("data", c_void_p), ("size", c_int)]
class Frame(Structure):
    _fields_ = [("data", c_void_p * 8), ("linesize", c_int * 8),
                ("extended_data", c_void_p), ("width", c_int), ("height", c_int),
                ("nb_samples", c_int), ("format", c_int)]

def bind(dll, name, res, *args):
    fn = getattr(dll, name)
    fn.argtypes, fn.restype = args, res
    return fn
ptr = c_void_p
codec_open = bind(codec, "avcodec_open2", c_int, ptr, ptr, ptr)
codec_alloc = bind(codec, "avcodec_alloc_context3", ptr, ptr)
find_decoder = bind(codec, "avcodec_find_decoder_by_name", ptr, c_char_p)
find_encoder = bind(codec, "avcodec_find_encoder_by_name", ptr, c_char_p)
packet_alloc = bind(codec, "av_packet_alloc", POINTER(Packet))
packet_new = bind(codec, "av_new_packet", c_int, POINTER(Packet), c_int)
packet_unref = bind(codec, "av_packet_unref", None, POINTER(Packet))
frame_alloc = bind(avutil, "av_frame_alloc", POINTER(Frame))
send_packet = bind(codec, "avcodec_send_packet", c_int, ptr, POINTER(Packet))
recv_frame = bind(codec, "avcodec_receive_frame", c_int, ptr, POINTER(Frame))
sws_get = bind(sws, "sws_getContext", ptr, c_int, c_int, c_int, c_int, c_int, c_int, c_int, ptr, ptr, ptr)
sws_scale = bind(sws, "sws_scale", c_int, ptr, POINTER(ptr), POINTER(c_int), c_int, c_int, POINTER(ptr), POINTER(c_int))

def check(code):
    if code < 0:
        err = create_string_buffer(256)
        bind(avutil, "av_strerror", c_int, c_int, c_char_p, c_size_t)(code, err, len(err))
        raise RuntimeError(f"{code}: {err.value!r}")
    return code

def atoms(buf):
    off = 0
    while off < len(buf):
        size, kind = unpack_from(">I4s", buf, off)
        assert 8 <= size <= len(buf) - off
        yield kind, buf[off+8:off+size]
        off += size

def decode(path, raw=False):
    from PIL import Image
    file = Path(path).read_bytes()
    box = dict(atoms(file))
    for name in (b"moov", b"trak", b"mdia", b"minf", b"stbl"):
        box = dict(atoms(box[name]))
    entry = dict(atoms(box[b"stsd"][8:]))[b"avc1"]
    ext = dict(atoms(entry[78:]))
    config = ext[b"avcC"]
    length_size = (config[4] & 3) + 1
    offset = 6
    start = b"\0\0\0\1"
    head = []
    for count in (config[5] & 31, None):
        if count is None:
            count = config[offset]
            offset += 1
        for _ in range(count):
            n, = unpack_from(">H", config, offset)
            head.extend((start, config[offset+2:offset+2+n]))
            offset += 2+n
    sizes = box[b"stsz"]
    sample_size, count = unpack_from(">II", sizes, 4)
    assert sample_size == 0 and unpack_from(">I", box[b"stco"], 4)[0] == 1
    offset, = unpack_from(">I", box[b"stco"], 8)
    d = find_decoder(b"h264")
    ctx = codec_alloc(d)
    check(codec_open(ctx, d, None))
    pkt = packet_alloc()
    frame = frame_alloc()
    scale_ctx = None
    print("avc1 children", list(ext), "avcC", config.hex(), "output RGB encoder", bool(find_encoder(b"libx264rgb")), flush=True)
    def drain():
        nonlocal scale_ctx
        while True:
            status = recv_frame(ctx, frame)
            if status in (-11, -541478725):
                break
            check(status)
            f = frame.contents
            w, h = f.width, f.height
            if raw:
                import numpy as np
                assert f.format == 0
                planes = []
                for i, (rows, cols) in enumerate(((h,w), (h//2,w//2), (h//2,w//2))):
                    stride = f.linesize[i]
                    planes.append(np.frombuffer(string_at(f.data[i], rows * stride), dtype=np.uint8).reshape(rows,stride)[:,:cols].copy())
                yield planes
                continue
            if scale_ctx is None:
                print("decoded:", w, h, f.format, list(f.linesize), flush=True)
                scale_ctx = sws_get(w, h, f.format, w, h, 2, 0x10, None, None, None)
                assert scale_ctx
            rgb = create_string_buffer(w * h * 3 + 64)
            out = (ptr * 4)(addressof(rgb))
            lines = (c_int * 4)(w * 3)
            assert sws_scale(scale_ctx, f.data, f.linesize, 0, h, out, lines) == h
            yield Image.frombytes("RGB", (w, h), rgb.raw[:w*h*3])
    for i in range(count):
        size, = unpack_from(">I", sizes, 12+4*i)
        sample = file[offset:offset+size]
        offset += size
        j = 0
        nals = head.copy() if not i else []
        while j < size:
            n = int.from_bytes(sample[j:j+length_size], "big")
            j += length_size
            nals.extend((start, sample[j:j+n]))
            j += n
        assert j == size
        data = b"".join(nals)
        check(packet_new(pkt, len(data)))
        memmove(pkt.contents.data, data, len(data))
        check(send_packet(ctx, pkt))
        packet_unref(pkt)
        yield from drain()
    check(send_packet(ctx, None))
    yield from drain()

if __name__ == "__main__":
    from PIL import Image
    root = Path(__file__).parent
    preview = Image.new("RGB", (1280, 800))
    for i, frame in enumerate(decode(sys.argv[1])):
        frame.save(root / f"src{i:02}.png", compress_level=1)
        if i == 0:
            frame.resize((640, 640), Image.Resampling.NEAREST).save(root / "first.png")
        preview.paste(frame.resize((160, 160), Image.Resampling.NEAREST), ((i % 8)*160, (i//8)*160))
    preview.save(root / "source.png")
    print("frames", i+1)
