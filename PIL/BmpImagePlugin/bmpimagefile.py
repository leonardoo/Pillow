from PIL import Image, ImageFile, ImagePalette

from .bmpimageformat import base

from . import utils


# ==============================================================================
# Image plugin for the Windows BMP format.
# ==============================================================================
class BmpImageFile(ImageFile.ImageFile):
    """ Image plugin for the Windows Bitmap format (BMP) """

    # ------------------------------------------------------------- Description
    format_description = "Windows Bitmap"
    format = "BMP"
    # -------------------------------------------------- BMP Compression values
    COMPRESSIONS = {'RAW': 0, 'RLE8': 1, 'RLE4': 2,
                    'BITFIELDS': 3, 'JPEG': 4, 'PNG': 5}
    RAW, RLE8, RLE4, BITFIELDS, JPEG, PNG = 0, 1, 2, 3, 4, 5

    SUPPORTED = {32: [(0xff0000, 0xff00, 0xff, 0x0),
                      (0xff0000, 0xff00, 0xff, 0xff000000),
                      (0x0, 0x0, 0x0, 0x0)],
                 24: [(0xff0000, 0xff00, 0xff)],
                 16: [(0xf800, 0x7e0, 0x1f), (0x7c00, 0x3e0, 0x1f)]}
    MASK_MODES = {(32, (0xff0000, 0xff00, 0xff, 0x0)): "BGRX",
                  (32, (0xff0000, 0xff00, 0xff, 0xff000000)): "BGRA",
                  (32, (0x0, 0x0, 0x0, 0x0)): "BGRA",
                  (24, (0xff0000, 0xff00, 0xff)): "BGR",
                  (16, (0xf800, 0x7e0, 0x1f)): "BGR;16",
                  (16, (0x7c00, 0x3e0, 0x1f)): "BGR;15"}

    def _bitmap(self, header=0, offset=0):
        """ Read relevant info about the BMP """
        read, seek = self.fp.read, self.fp.seek
        if header:
            seek(header)
        file_info = dict()
        file_info['header_size'] = utils.i32(read(4))  # read bmp header size @offset 14 (this is part of the header size)
        file_info['direction'] = -1
        # --------------------- If requested, read header at a specific position
        header_data = ImageFile._safe_read(self.fp, file_info['header_size'] - 4)  # read the rest of the bmp header, without its size

        if file_info['header_size'] in (12, 40, 64, 108, 124):  # valid bitmaps
            # ---------------------------------------------- IBM OS/2 Bitmap v1
            # - This format has different offsets because of width/height types
            if file_info['header_size'] == 12:
                bmpformat = base.BmpImageFormat12(header_data, 3,
                                                  compression=self.RAW)
            # ----------------------------------------- Windows Bitmap v2 to v5
            else:  # v3 and OS/2
                bmpformat = base.BmpImageFormat(header_data, 4)
                bmpformat.read = read
        else:
            raise IOError("Unsupported BMP header type (%d)" % file_info['header_size'])

        file_info.update(bmpformat.process_info())
        # ------------------ Special case : header is reported 40, which
        # ---------------------- is shorter than real size for bpp >= 16
        self.size = file_info['width'], file_info['height']
        # -------- If color count was not found in the header, compute from bits
        file_info['colors'] = file_info['colors'] if file_info.get('colors', 0) else (1 << file_info['bits'])
        # -------------------------------- Check abnormal values for DOS attacks
        if file_info['width'] * file_info['height'] > 2**31:
            raise IOError("Unsupported BMP Size: (%dx%d)" % self.size)
        # ----------------------- Check bit depth for unusual unsupported values
        self.mode, raw_mode = utils.BIT2MODE.get(file_info['bits'], (None, None))
        if self.mode is None:
            raise IOError("Unsupported BMP pixel depth (%d)" % file_info['bits'])
        # ----------------- Process BMP with Bitfields compression (not palette)
        raw_mode = self.compression(file_info, header)
        # ---------------- Once the header is processed, process the palette/LUT
        self.palette(file_info, read)
        # ----------------------------- Finally set the tile data for the plugin
        self.tile = [('raw', (0, 0, file_info['width'], file_info['height']), offset or self.fp.tell(),
                      (raw_mode, ((file_info['width'] * file_info['bits'] + 31) >> 3) & (~3), file_info['direction'])
                      )]

    def _mask_modes(self, file_info, rgb=True):
        key = "rgb{0}_mask".format("" if rgb else "a")
        return self.MASK_MODES(file_info['bits'], file_info[key])

    def _open(self):
        """ Open file, check magic number and read header """
        # read 14 bytes: magic number, filesize, reserved, header final offset
        head_data = self.fp.read(14)
        # choke if the file does not have the required magic bytes
        if head_data[0:2] != b"BM":
            raise SyntaxError("Not a BMP file")
        # read the start position of the BMP image data (u32)
        offset = utils.i32(head_data[10:14])
        # load bitmap information (offset=raster info)
        self._bitmap(offset=offset)

    def _supported(self, file_info):
        return self.SUPPORTED[file_info['bits']]

    def is_supported(self, file_info):
        return file_info['bits'] in self.SUPPORTED

    def compression(self, file_info, header):
        if file_info['compression'] == self.BITFIELDS:
            if self.is_supported():
                supported = self._supported(file_info)
                if file_info['bits'] == 32 and file_info['rgba_mask'] in supported:
                    raw_mode = self._mask_modes(file_info, False)
                    self.mode = "RGBA" if raw_mode in ("BGRA",) else self.mode
                elif file_info['bits'] in (24, 16) and file_info['rgb_mask'] in supported:
                    raw_mode = self._mask_modes(file_info)
                else:
                    raise IOError("Unsupported BMP bitfields layout")
            else:
                raise IOError("Unsupported BMP bitfields layout")
        elif file_info['compression'] == self.RAW:
            if file_info['bits'] == 32 and header == 22:  # 32-bit .cur offset
                raw_mode, self.mode = "BGRA", "RGBA"
        else:
            raise IOError("Unsupported BMP compression (%d)" % file_info['compression'])

        self.info['compression'] = file_info['compression']
        return raw_mode

    def pallete(self, file_info, read):
        # ---------------- Once the header is processed, process the palette/LUT
        if self.mode == "P":  # Paletted for 1, 4 and 8 bit images
            # ----------------------------------------------------- 1-bit images
            if not (0 < file_info['colors'] <= 65536):
                raise IOError("Unsupported BMP Palette size (%d)" % file_info['colors'])
            else:
                padding = file_info['palette_padding']
                palette = read(padding * file_info['colors'])
                greyscale = True
                indices = (0, 255) if file_info['colors'] == 2 else list(range(file_info['colors']))
                # ------------------ Check if greyscale and ignore palette if so
                for ind, val in enumerate(indices):
                    rgb = palette[ind*padding:ind*padding + 3]
                    if rgb != utils.o8(val) * 3:
                        greyscale = False
                # -------- If all colors are grey, white or black, ditch palette
                if greyscale:
                    self.mode = "1" if file_info['colors'] == 2 else "L"
                    raw_mode = self.mode
                else:
                    self.mode = "P"
                    self.palette = ImagePalette.raw("BGRX" if padding == 4 else "BGR", palette)

