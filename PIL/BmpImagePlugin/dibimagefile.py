from .bmpimagefile import BmpImageFile


# ==============================================================================
# Image plugin for the DIB format (BMP alias)
# ==============================================================================
class DibImageFile(BmpImageFile):

    format = "DIB"
    format_description = "Windows Bitmap"

    def _open(self):
        self._bitmap()
