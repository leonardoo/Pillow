#
# The Python Imaging Library.
# $Id$
#
# BMP file handler
#
# Windows (and OS/2) native bitmap storage format.
#
# history:
# 1995-09-01 fl   Created
# 1996-04-30 fl   Added save
# 1997-08-27 fl   Fixed save of 1-bit images
# 1998-03-06 fl   Load P images as L where possible
# 1998-07-03 fl   Load P images as 1 where possible
# 1998-12-29 fl   Handle small palettes
# 2002-12-30 fl   Fixed load of 1-bit palette images
# 2003-04-21 fl   Fixed load of 1-bit monochrome images
# 2003-04-23 fl   Added limited support for BI_BITFIELDS compression
#
# Copyright (c) 1997-2003 by Secret Labs AB
# Copyright (c) 1995-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.7"


from .utils import i8, i16, i32, o8, o16, o32, BIT2MODE, SAVE
from PIL import Image, ImageFile
from .bmpimagefile import BmpImageFile
from .dibimagefile import DibImageFile

#
# --------------------------------------------------------------------
# Read BMP file


def _accept(prefix):
    return prefix[:2] == b"BM"


#
# --------------------------------------------------------------------
# Write BMP file

def _save(im, fp, filename, check=0):
    try:
        rawmode, bits, colors = SAVE[im.mode]
    except KeyError:
        raise IOError("cannot write mode %s as BMP" % im.mode)

    if check:
        return check

    info = im.encoderinfo

    dpi = info.get("dpi", (96, 96))

    # 1 meter == 39.3701 inches
    ppm = tuple(map(lambda x: int(x * 39.3701), dpi))

    stride = ((im.size[0]*bits+7)//8+3) & (~3)
    header = 40  # or 64 for OS/2 version 2
    offset = 14 + header + colors * 4
    image = stride * im.size[1]

    # bitmap header
    fp.write(b"BM" +                      # file type (magic)
             o32(offset+image) +          # file size
             o32(0) +                     # reserved
             o32(offset))                 # image data offset

    # bitmap info header
    fp.write(o32(header) +                # info header size
             o32(im.size[0]) +            # width
             o32(im.size[1]) +            # height
             o16(1) +                     # planes
             o16(bits) +                  # depth
             o32(0) +                     # compression (0=uncompressed)
             o32(image) +                 # size of bitmap
             o32(ppm[0]) + o32(ppm[1]) +  # resolution
             o32(colors) +                # colors used
             o32(colors))                 # colors important

    fp.write(b"\0" * (header - 40))       # padding (for OS/2 format)

    if im.mode == "1":
        for i in (0, 255):
            fp.write(o8(i) * 4)
    elif im.mode == "L":
        for i in range(256):
            fp.write(o8(i) * 4)
    elif im.mode == "P":
        fp.write(im.im.getpalette("RGB", "BGRX"))

    ImageFile._save(im, fp, [("raw", (0, 0)+im.size, 0,
                    (rawmode, stride, -1))])

#
# --------------------------------------------------------------------
# Registry

Image.register_open(BmpImageFile.format, BmpImageFile, _accept)
Image.register_save(BmpImageFile.format, _save)

Image.register_extension(BmpImageFile.format, ".bmp")

Image.register_mime(BmpImageFile.format, "image/bmp")
