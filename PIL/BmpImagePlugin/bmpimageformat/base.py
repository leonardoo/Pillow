from PIL.bmpimageplugin.utils import i8, i16, i32

from ..bmpimageplugin import BmpImageFile


class BaseBmpImageFormat(object):

    file_info = {}
    LEN = None

    def __init__(self, header_data, palette_padding):
        self._header_data = header_data
        self.file_info['palette_padding'] = palette_padding

    def process_info(self):
        return self._process(self.file_info)

    def _process(self, file_info):
        file_info['width'], file_info['height'] = self.get_width_heigth()
        file_info['planes'], file_info['bits'] = self.get_planes_bits()
        return file_info

    def get_width_heigth(self):
        size = self._header_data[0:self.LEN*2]
        width = self.METHOD(size[:self.LEN])
        height = self.METHOD(size[self.LEN:])
        return width, height

    def get_planes_bits(self):
        init = self.LEN * 2
        end = init + 4
        size = self._header_data[init:planes]
        planes = i16(size[:len(size)/2])
        bits = i16(size[len(size)/2:])
        return planes, bits


class BmpImageFormat12(BaseBmpImageFormat):

    LEN = 2
    METHOD = i16

    def __init__(self, **kwargs):
        compression = kwargs.get("compression")
        super(BmpImageFormat12, self).__init__(*kwargs)
        self.file_info['compression'] = self.RAW


class BmpImageFormat(BaseBmpImageFormat):

    LEN = 4
    METHOD = i32

    def get_width_heigth(self, **kwargs):
        width, height = super(BmpImageFormat, self).get_width_heigth(**kwargs)
        if file_info['y_flip']:
            height = 2**32 - height
        return width, height

    def _process(self, file_info):
        file_info['y_flip'] = i8(header_data[7]) == 0xff
        file_info['direction'] = 1 if file_info['y_flip'] else -1
        file_info = super(BmpImageFormat, self)._process(file_info)
        file_info['compression'] = i32(header_data[12:16])
        file_info['data_size'] = i32(header_data[16:20])  # byte size of pixel data
        file_info['pixels_per_meter'] = (i32(header_data[20:24]), i32(header_data[24:28]))
        file_info['colors'] = i32(header_data[28:32])
        file_info['palette_padding'] = 4
        self.info["dpi"] = tuple(map(lambda x: int(math.ceil(x / 39.3701)), file_info['pixels_per_meter']))
        if file_info['compression'] == BmpImageFile.BITFIELDS:
            if len(header_data) >= 52:
                for idx, mask in enumerate(['r_mask', 'g_mask', 'b_mask', 'a_mask']):
                    file_info[mask] = i32(header_data[36+idx*4:40+idx*4])
            else:
                for mask in ['r_mask', 'g_mask', 'b_mask', 'a_mask']:
                    file_info[mask] = i32(self.read(4))
        file_info['rgb_mask'] = (file_info['r_mask'], file_info['g_mask'], file_info['b_mask'])
        file_info['rgba_mask'] = (file_info['r_mask'], file_info['g_mask'], file_info['b_mask'], file_info['a_mask'])
